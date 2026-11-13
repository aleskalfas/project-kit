# Gaps: what the engine and libraries would need to draw these pages (round 4)

Each item names its owner: the foundations, the neutral brand, the starter library, the `pkit` notation, or the engine. Items new or changed in round 4 are marked *new*, *changed* or *withdrawn*. Records that bound a change are named where they apply. Each change to a shipped library declares a changeset for the capability (DEC-013 point 4, PRJ-002).

## Foundations: roles every brand fills

1. **An ordered ramp per family:** `family.<hue>.ramp.1`–`5`, one set per mode. Each step holds 3:1 or more against the paper, and 4.5:1 against one text tone shared by all five steps.
2. *Changed.* **A focus role, in place of round 3's accent:** `focus.text` and `focus.tint`. It means one thing: what the page's point is about. `focus.text` holds 4.5:1 on the paper, on the tint and on the panel. The tint is never the only cue. A brand may take the focus hue from its ramp's family, so one accent serves both, as neutral does (item 12).
3. **Type roles:** title 48/56; lead 30/38 in the primary text tone; head 24/32 semibold; body 24/32; small 20/28 (furniture: the source line, a row's tag, a caption); code 22/28 for every monospace run, inline included.
4. **A spacing scale:** 4, 8, 12, 16, 24, 32, 48, 64.
5. **A tertiary text tone:** `text-muted`, for prompts, tree guides, placeholders, captions and the source line. It holds 4.5:1 on the panel too.
6. *Changed.* **An outline role at 3:1:** `border-strong`, now the line of every container, not only of sockets and the dashed box. It holds 3:1 on the paper and on the focus tint.
7. *Changed.* **A keyline role:** `border-subtle`, now only for a divider inside a container (a slot row, the caveat divider). It is never the only boundary of a thing. Round 3's use as a panel edge is withdrawn: a panel is a fill only.
8. *Withdrawn.* **The tag fill role.** A role is now a container's heading, not a pill.
9. **A relation role:** the neutral colour of arrows and wires.
10. *Changed.* **Radius and stroke tokens:** radius 8 (elbows too); **one stroke, 2 px, for every line**; arrow-head 12. Round 3's 1 px keyline token is withdrawn.
11. *New.* **A panel role:** `surface-panel`, a terminal's fill. Lighter than the paper in dark. A panel takes no line.

## Neutral brand: the values it ships

12. *Changed.* **One accent, green, in two forms:** the ramp (light L .30 → .55, white text on all five; dark L .89 → .615, paper text on all five) and the focus pair (light text `#047554` at L .50, tint `#dff7eb`; dark text `#91debc`, tint `#112d21`). Values are in `design-system.md` 4.2 and 4.3.
13. *Withdrawn.* **The blue accent** (round 3). Its two uses split: "refused" became an outcome (item 21), and "the slot in focus" became the focus form.
14. **Tonal scales** in OKLCH, one lightness per step across hues; **a designed dark mode**; **font naming** for the semibold (`Source Sans Pro` at weight 600, since resvg does not resolve "Source Sans Pro Semibold"); **no new font**.
15. Neutral declares `open: []`. None of the above opens a role to a brand built on neutral; they are values neutral itself would ship. Making any of them overridable is a change to neutral's contract (COR-014; DEC-001 point 9) and the maintainer's call.

## Foundations, `deck`: the slide frame

16. **A slide grid:** 12 × 64, gutters 32, side margins 80, the title's cap height on a 64 px top margin, lead baselines 140 and 178, the field from 224 to 608, the source line's baseline at 656.
17. **A lead set as given lines,** broken by sense, measured against the frame.
18. **One source line role:** "In project-kit: …", 20 px muted, one line, no code runs.

## Starter library: patterns and their options

Each is a DEC-007 decision for the starter's owner. One job per pattern (point 2) decides between an option and a new pattern. The entry bar (point 3) asks for reference renders of each option, one in a text-heavy language. The README's boundaries table changes with it.

19. **`layers` stepped:** centred levels, each one step wider than the level above, shaded from the ordered ramp by place.
20. *Changed.* **`layers` stepped relations:** up to two relations that walk the steps at a set offset outside the stepped edge (16). Each runs down the middle of each tread, rounds each outer corner on a concentric arc and goes sharp into each inner corner. Each leaves the first level's side and lands on the last level's top tread. The notes stand at the foot, each in its own column, last lines on the last level's last baseline. Round 3's straight flank arrows are withdrawn: a straight line cannot hold one distance from a stepped edge.
21. *Changed.* **An outcome cell:** an ink mark with its word beside it in regular weight, then the reason in the focus text and the strong weight. No tint and no hue on the mark.
22. *Changed.* **A flow-headed table:** stage names in the strong weight on 2 px rules from a ramp, the rules joined by connectors. Rows on two shared baselines, with every cell's text on its column's edge.
23. *Changed.* **A limit band:** a divider across the table, and at least 48 px (and more than the row gap) above the limit. "Limit:" with a colon in the strong weight, then the limit, body size.
24. *Changed.* **A numbered step:** a disc with the number, the step's name beside it, its panel 12 under it; steps 24 apart, in reading order.
25. *Changed.* **`code` panels sized to their content:** a panel takes the width of its longest line plus its padding, never a column's width. A command is never broken.
26. *Changed.* **Lines in focus in `code`:** the given lines take the focus tint edge to edge, 12 px clear of the text above and inside. Round 3's 4 px accent rule at the left is withdrawn (one stroke weight).
27. **A tree in tree notation:** guides in the muted tone, names in mono, an optional tag per entry; never drawn under a prompt.
28. *Changed.* **`connector` attachment rules:** a connector starts on its source's edge and ends on its target's edge. Elbows sit on the deck's radius. It keeps at least 16 px from any shape it does not attach to. *New:* a connector into a container lands on the compartment it relates to, and no two connectors cross.
29. **Inline code at the code size** (22 inside 24 px text).
30. *New.* **A container with compartments:** a 2 px outline at 3:1, a heading split off by an outline-tone divider, and compartments wall to wall split by keyline dividers. One part may take the focus tint, square-cornered inside the wall.

## The `pkit` notation

31. *Changed.* **No hue of its own.** Round 3's violet for pkit's files is withdrawn. The notation now says which of pkit's things take the brand's focus form on a page: pkit's files where ownership is the point (page 2), the proven slot and its proof (page 4). Yours take ink.
32. **The layers as a ramp:** the five layers take the ramp's steps by place, naming no concept, since each lower layer holds pkit's and yours (DEC-001 point 6, its own pyramid example). Changing DEC-001 itself is the maintainer's call; this asks only that the piece name no concept on those levels.
33. *Changed.* **A capability in its role as one form:** the starter's container headed by the role id (mono, ink), with the capability's name second (sans, ink-soft). The same form serves the opener (large, with its slots) and each filler (small). Round 3's block with a role tag is withdrawn.
34. *Changed.* **A slot as a compartment** of the opener's container, wall to wall, carrying its real id and its purpose. A tie that fills it lands on the container's wall at its row. Round 3's socket is withdrawn: its opening read as a shift, not a socket.
35. **Second cues for ownership:** the owner's word beside the entry, and position, rather than marks.

## Engine: typesetting and measurement

36. **Czech binding:** one-letter words bound to the next; "ve" kept with its noun.
37. **No lone last word** in a wrapped block.
38. **Glyph fallback by run:** split a run at any glyph its font lacks.
39. **Measured text in patterns:** size boxes from the shipped fonts' advance widths.
40. **Arrowheads that meet their target:** the line stops at the head's base.
41. **No-break space in commands** (`rm -r`, `git push -f`).
42. *New.* **Elbows on arcs with a set radius per corner:** a connector's path takes a radius at each corner, 0 for a sharp one, drawn as true arcs. The stepped relations need concentric arcs to hold their offset.
43. *Changed.* **Craft checks on every render** (`tools/svg.py`, `check`). Round 3's checks stay: wire clearance to shapes (16) and text (12), text against the sides of what holds it (12), the margins. Round 4 adds wire ends on their shapes' edges, the offset of a following wire (±0.6 px), no crossings, one stroke weight, 3:1 for every container's line and block's fill, no line on a panel, 12 px around every highlight, even insets (24) in every container and panel, and the left edges in each named column. All 16 renders pass with no fault.
