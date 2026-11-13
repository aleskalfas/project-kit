# Gaps: what the engine and libraries would need to draw these pages (round 2)

Each item names its owner: the foundations, the neutral brand, the starter library, the `pkit` notation, or the engine. Items new or changed in round 2 are marked *new* or *changed*. Records that bound the change are named where they apply.

## Foundations: roles every brand fills

1. *Changed.* **An ordered ramp per family:** `family.<hue>.ramp.1`–`5`, one set per mode, **each step at 3 to 1 or more against the paper**, with a paired text tone per step at 4.5 to 1. A pattern that shades by place has no ordered colour today.
2. **A strong text tone per family:** `family.<hue>.strong`, for text on the family's own fill.
3. *Changed.* **Type roles:** title 48/56, lead 24/32, head 24/32 semibold, body 24/32, small 20/28 (furniture only), code 22/28. The shipped sizes (24 / 16 / 14) cannot reach a projected slide's 24 px body.
4. **A spacing scale:** 4, 8, 16, 24, 32, 48, 64.
5. **A tertiary text tone:** `text-muted`, for prompts, comments and the source line.
6. *New.* **An outline role at 3 to 1:** `border-strong`, for an outline a reader must see (a dashed "undecided" box, a list's rule). The shipped border is a hairline at about 1.4 to 1, right for grouping, invisible for meaning.
7. *New.* **A relation role:** `relation`, the neutral colour of arrows and wires, so a connector never borrows a concept's hue.
8. **Radius and stroke tokens:** radius 8, `stroke.hair` 1, `stroke.connector` 2, `arrow-head` 12.

## Neutral brand: the values it ships

9. **Tonal scales:** 11 steps per hue and for the greys, in OKLCH, one lightness per step across hues.
10. *Changed.* **A designed dark mode:** near-black paper, a raised surface, low-chroma tints, and a ramp whose step 1 is the lightest, every step at 3 to 1 or more.
11. **Font naming for the semibold:** `Source Sans Pro` at weight 600 (name ID 16); resvg does not resolve "Source Sans Pro Semibold".
12. **No new font needed.**
13. Neutral declares `open: []`. None of the above opens a role to a brand built on neutral; they are values neutral itself would ship. If any is meant to be overridable, that is a change to neutral's contract (COR-014; DEC-001 point 9) and the maintainer's call.

## Foundations, `deck`: the slide frame

14. *Changed.* **A slide grid:** 12 × 64 px, gutters 32, side margins 80, the title's cap height on a 64 px top margin, **a field from 208 to 608, and the source line's baseline at 656, so the bottom margin equals the top one**.
15. **A lead set as given lines,** broken by sense.
16. *New.* **One source line role:** "In project-kit: …" evidence, 20 px muted, one line, the same place on every page.

## Starter library: patterns and their options

Each is a DEC-007 decision for the starter's owner: one job per pattern (point 2) decides option or new pattern; the entry bar (point 3) asks for reference renders of each option and one in a text-heavy language; the README's boundaries table changes with it.

17. **`layers` stepped:** centred levels, each one step wider than the level above, filled from the ordered ramp by place, a name and a description centred in each.
18. *New.* **`layers` flank relations:** an option drawing up to two relations as straight arrows parallel to the stack's flanks (down on the left, up on the right), each with its note beside its middle and clear of it.
19. **A head and text inside a level,** sized to the longest name.
20. **A flow-headed table:** chevron column heads from a ramp, row head plus tag, cells in body type with at most two lines.
21. *Changed.* **A limit:** one pattern, "Limit:" with a colon in the strong weight, the limit in the secondary tone, in body type.
22. *New.* **A numbered step:** a disc holding the step's number, its name beside it, its panel under it; `panels` places steps in one row of equal panels.
23. *New.* **A labelled list with a rule:** a label in two parts (the owner in its colour, then what that means), a 4 px rule in the owner's colour, items in mono.
24. **Code roles:** prompt, continuation prompt, command, argument, comment, output, each with its own tone, plus concept runs in the notation's colours.
25. *New.* **A long command broken by the shell, not the typesetter:** `code` should break an over-long command at given points with a trailing backslash and a `> ` continuation prompt, never wrap it.
26. **A check-marked list:** a ✓ marker in the muted tone.
27. *New.* **Inline code at the running size:** a code run inside a sentence takes the sentence's size, not the code role's.

## The `pkit` notation

28. *Changed.* **One meaning per hue:** `pkit/core` violet (pkit's files); a new `pkit/role` blue; `pkit/capability` orange; `pkit/yours` **no hue** (ink). Today `yours` is blue, and the showcase's roles borrow `core`'s violet, which gave violet two meanings.
29. **The layers as a ramp:** the five layers take the steps of the green ramp by place, naming no concept, since a level holds both pkit's and yours (DEC-001 point 6, its own pyramid example). Changing DEC-001 itself is the maintainer's call; this asks only that the piece name no concept on those levels.
30. *New.* **A role frame:** `pkit/role` draws as a 2 px frame with the role's name on its top edge in monospace; the capability that plays it sits inside as a card.
31. *New.* **A slot on a role's edge:** a slot opened under a role draws as an outlined row on the role frame's left edge, and a tie that fills it ends on that edge, never on the opener's card.
32. **Second cues for ownership:** position and a label, now, rather than ●/○ marks (round 1's marks were 8 px across on the slide).

## Engine: typesetting

33. **Czech binding:** bind the one-letter words (v, k, s, z, o, u, a, i) to the next word.
34. *New.* **No lone last word:** when a wrapped block's last line holds one word, bring the word before it down (`tools/svg.py` does this).
35. **Glyph fallback by run:** split a run at any glyph its font lacks.
36. **Measured text in patterns:** size boxes from the shipped fonts' advance widths (`tools/measure.py`).
37. **Arrowheads that meet their target:** the line stops at the head's base.
38. *New.* **No-break space in commands:** a command such as `rm -r` must not break at its space.
