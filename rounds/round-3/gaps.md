# Gaps: what the engine and libraries would need to draw these pages (round 3)

Each item names its owner: the foundations, the neutral brand, the starter library, the `pkit` notation, or the engine. Items new or changed in round 3 are marked *new* or *changed*. Records that bound a change are named where they apply. Each change to a shipped library declares a changeset for the capability (DEC-013 point 4, PRJ-002).

## Foundations: roles every brand fills

1. *Changed.* **An ordered ramp per family:** `family.<hue>.ramp.1`–`5`, one set per mode, each step at 3 to 1 or more against the paper **and at 4.5 to 1 against one text tone shared by all five steps**, so the text never changes colour along an order.
2. *New.* **An accent role:** `accent.tint`, `accent.line`, `accent.text`, for the one emphasis a page has (a highlighted cell, a highlighted slot, highlighted lines). Distinct from every concept hue.
3. *Changed.* **Type roles:** title 48/56; **lead 30/38 in the primary text tone** (the page's point); head 24/32 semibold; body 24/32; small 20/28 (furniture only); code 22/28 for every monospace run, inline included.
4. **A spacing scale:** 4, 8, 12, 16, 24, 32, 48, 64.
5. **A tertiary text tone:** `text-muted`, for prompts, tree guides, placeholders and the source line.
6. **An outline role at 3 to 1:** `border-strong`, for an outline that carries meaning.
7. *New.* **A keyline role:** `border-subtle` at about 1.5 to 1, a container's 1 px edge so a panel holds on a projector.
8. *New.* **A tag fill role:** `surface-tag`, a filled pill readable against both the paper and the surface.
9. **A relation role:** the neutral colour of arrows and wires.
10. **Radius and stroke tokens:** radius 8 (elbows too), keyline 1, stroke 2, arrow-head 12.

## Neutral brand: the values it ships

11. *Changed.* **The retuned green ramp:** light L .30 → .55 (white text on all five), dark L .89 → .615 (paper text on all five); values in `design-system.md` 4.2.
12. *New.* **A blue accent** in both modes (`design-system.md` 4.3).
13. **Tonal scales** in OKLCH, one lightness per step across hues; **a designed dark mode**; **font naming** for the semibold (`Source Sans Pro` at weight 600; resvg does not resolve "Source Sans Pro Semibold"); **no new font**.
14. Neutral declares `open: []`. None of the above opens a role to a brand built on neutral; they are values neutral itself would ship. Making any of them overridable is a change to neutral's contract (COR-014; DEC-001 point 9) and the maintainer's call.

## Foundations, `deck`: the slide frame

15. *Changed.* **A slide grid:** 12 × 64, gutters 32, side margins 80, the title's cap height on a 64 px top margin, **lead baselines 140 and 178, the field from 224 to 608**, the source line's baseline at 656.
16. **A lead set as given lines,** broken by sense, measured against the frame.
17. **One source line role:** "In project-kit: …", 20 px muted, one line, no code runs.

## Starter library: patterns and their options

Each is a DEC-007 decision for the starter's owner: one job per pattern (point 2) decides option or new pattern; the entry bar (point 3) asks for reference renders of each option, one in a text-heavy language; the README's boundaries table changes with it.

18. **`layers` stepped:** centred levels, each one step wider than the level above, shaded from the ordered ramp by place.
19. *Changed.* **`layers` flank relations:** up to two straight arrows parallel to the stair line through the levels' outer top corners, a set distance outboard at right angles; each note beside its arrow's middle, mirrored, flush toward it, at a set distance from the line.
20. *Changed.* **A flow-headed table:** stage blocks from a ramp joined by connectors (not chevrons), rows on two shared baselines without rules, and an option to mark one column as the outcome.
21. *New.* **An outcome cell:** the accent tint, a mark with its word beside it, a qualifier.
22. **A limit:** "Limit:" with a colon in the strong weight, then the limit, body size.
23. **A numbered step:** a disc with the number, the step's name beside it, its panel under it; steps stacked in reading order.
24. *Changed.* **`code` without breaks:** a command is never broken; a panel takes the width its longest line needs. Round 2's shell continuation (gap 25 then) is withdrawn.
25. *New.* **Highlighted lines in `code`:** given lines take the accent tint edge to edge, with a 4 px accent rule at the left.
26. *New.* **A tree in tree notation:** guides in the muted tone, names in mono, an optional tag per entry; never drawn under a prompt.
27. *New.* **`connector` attachment rules:** a connector starts on its source's edge and ends on its target's edge; two connectors from one side of a block leave at equal offsets about its middle; elbows on the deck's radius; at least 16 px from any shape it does not attach to.
28. **Inline code at the code size** (22 inside 24 px text).

## The `pkit` notation

29. *Changed.* **One meaning per hue:** `pkit/core` violet means pkit's files only; `pkit/yours` takes no hue (ink); **no hue for roles or capabilities** (round 2 asked for a blue `pkit/role` and an orange `pkit/capability`; withdrawn, since on a page where everything is pkit's a hue tells nothing apart, and shape carries the kinds).
30. **The layers as a ramp:** the five layers take the ramp's steps by place, naming no concept, since each lower layer holds pkit's and yours (DEC-001 point 6, its own pyramid example). Changing DEC-001 itself is the maintainer's call; this asks only that the piece name no concept on those levels.
31. *New.* **A capability as a block** with its name in the strong weight; **a role as a tag** (a filled pill straddling the block's top edge, monospace).
32. *New.* **A slot as a socket** cut into the opening capability's edge, facing its fillers, carrying its real id and its purpose; a tie that fills it ends in its mouth.
33. **Second cues for ownership:** the owner's word beside the entry, and position, rather than marks.

## Engine: typesetting and measurement

34. **Czech binding:** one-letter words bound to the next; "ve" kept with its noun.
35. **No lone last word** in a wrapped block.
36. **Glyph fallback by run:** split a run at any glyph its font lacks.
37. **Measured text in patterns:** size boxes from the shipped fonts' advance widths.
38. **Arrowheads that meet their target:** the line stops at the head's base.
39. **No-break space in commands** (`rm -r`, `git push -f`).
40. *New.* **Craft checks on every render** (`tools/svg.py`, `check`): each connector against every shape it does not attach to (16 px floor), each connector against text (12 px), each text against the sides of what holds it (12 px), everything inside the margins. All 16 renders pass with no fault.
