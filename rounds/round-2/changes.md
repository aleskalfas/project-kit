# Changes: each round 1 finding, and what round 2 did

Order follows `round-1/verdict.md`. Where a fix is at the root (the system), every page took it; the page entries then say only what was left. "Agreed" means the finding's fix was taken as stated; "differs" says how and why.

## Deck

| Finding | What round 2 did |
|---|---|
| Type scale 48 / 24 / 20 / 18: body below 24 | **System.** Body 24, nothing under 20, code 22 (`design-system.md` section 2). 20 px is kept only for page furniture: the source line and table row tags. Copy was cut to fit, never the type shrunk; every cut is listed in `design-rationale.md`. Agreed. |
| Bottom margin about 33 px against 80 at the sides | **System.** The source line's baseline is 64 px from the foot, equal to the top margin; the field ends at 608. Agreed. |
| The footer has a different job on each page | **System.** One role: "In project-kit: …", one fact from project-kit, counted or read from the repository. Agreed. |
| Four pages, four container languages | **System.** One panel (surface, no border) for content; ramp fills for layers; a 2 px hue outline only where the boundary is the meaning (roles and slots); a dashed outline only for "undecided"; no boxes for lists and tables (`design-system.md` section 6). Agreed. |
| Purple means two things; blue appears once | **System and notation.** Violet now means only pkit's files (page 2). Roles take blue (page 4). "Yours" takes no hue. Four hues, one meaning each, each with a second cue. Differs: the round 1 verdict's page 4 fix said "purple for roles"; that would keep violet's two meanings, so roles moved to blue instead. |
| Dark mode: the ramp's far end sinks; page 4's brown is muddy | **System.** The dark ramp runs light to mid, every step at 5 to 1 or more against the paper. Page 4 no longer has a brown fill. Agreed. |

## Page 1: How pkit fits together

| Finding | What round 2 did |
|---|---|
| [block] Contrast: the base fades (1.18 to 1) | **System.** The ramp is rebuilt: light 12.3 → 3.2 to 1, dark 13.4 → 5.0 to 1. Agreed. |
| [block] The two relations are not drawn between the layers | **Page.** "Carried out" runs down the left flank, "checked first" up the right, both from the second level to the base. Agreed, with one difference: each relation's note sits beside its own arrow, left and right, not both in the left column, so each label is next to what it labels (Mayer: spatial contiguity). The left column keeps the ideas note. |
| [block] Notes and descriptions at 20 px | **System.** All at 24. Notes cut to one sentence each; three level descriptions shortened. |
| [polish] The up arrow ends 5 px below the foot | Both arrows now end exactly level with the base's foot. |
| [polish] "COR-065" in the footer | Dropped. |
| [polish] Czech padding in the second level | Rechecked at 24 px: 26 px a side in Czech, 40 in English. |

## Page 2: Install pkit

| Finding | What round 2 did |
|---|---|
| [block] The listing is labelled as `tree` output but is not | **Page.** No prompt over the listing. It is drawn as a diagram: two labelled lists of real paths. No line in the deck now sits under a command that could not print it. Agreed. |
| [block] Nothing marks the two steps as steps | **Page.** Two numbered discs and names over two equal panels in one row across the full width. The URL is broken with the shell's own continuation (`\` and bash's `> ` prompt), so it fits and still runs. Agreed. |
| [block] The aside outranks the message | **Page.** The aside is one body-size line in ink-soft; the steps carry the only heads. Agreed. |
| [block] pkit's files and yours differ in hue only | **Page.** Apart by position (left and right lists), by label, by lightness (violet against ink) and by a rule in each list's colour. The 8 px marks are gone. Agreed. |
| [block] Code 18 px across 11 lines | **System and page.** Code 22 px; the listing cut to four rows a side. Agreed. |
| [block] Two container languages; marks in different columns; the `● ○ …` row | **Page.** Commands are panels; files are lists with rules; the marks and the ellipsis row are gone. Agreed. |
| [polish] The key line comes last | The key is gone; each list is labelled directly above itself. |
| [polish] `pkit status` in prose type in the footer | The footer now states a different fact. Every command in the deck is monospace. |

## Page 3: Where permissions come from

| Finding | What round 2 did |
|---|---|
| [block] The chevrons fade (1.18 and 1.81 to 1) | **System.** Ramp steps 3 to 5 now hold 6.5, 4.8 and 3.2 to 1 in light, 8.5, 6.6 and 5.0 in dark. Agreed. |
| [block] Cells, sub-labels, limit and evidence at 20 px | **System and page.** Cells, limit and source fact at 24 or the furniture's 20; cells cut to phrases, two lines at most in both languages. Row tags stay at 20 px as a qualifier, the scale's smallest step. Agreed, except for the tags. |
| [polish] Lone last words in cells | **Engine.** The wrapper now never leaves one word alone on a last line, on every page. |
| [polish] "Limit" run-in with no separator | **Shared pattern.** "Limit:" with a colon, semibold, then ink-soft text, in body type. |
| [polish] The evidence repeats row 3 | Replaced by a different fact: 14 denies and 63 allows in Claude Code's settings, written by pkit. |
| [polish] "project-management" the only orange word | Set in ink-soft like the other tags; orange is keyed only where capabilities are the subject. |
| Czech: third column within 5 px of the margin | Every line in every render was measured; none passes x 1200. |

## Page 4: How capabilities work together

| Finding | What round 2 did |
|---|---|
| [block] The diagram shows capabilities naming each other | **Page.** Roles are blue frames with their names on their edges; each capability sits inside its role's frame as its occupant; the three slots sit on the `pkit::work-tracking` frame's own edge; each wire leaves a filler's frame and ends on that edge. No wire touches the project-management card. Agreed, with one difference: wires start at the filler's frame rather than a chip, because a contribution is declared by the capability (living-docs' `package.yaml`: `point: pkit::work-tracking:fixers`) and the frame is the capability in its role. |
| [block] The benefit list outranks the evidence | **Page.** Benefits are body size in ink-soft; the diagram's names are semibold and coloured. Agreed. |
| [block] A palette no other page uses | **System.** Capabilities sit in the deck's one panel; names in orange; roles in blue. Agreed, except that roles take blue, not purple (see Deck). |
| [block] Wiring and padding rough | **Page.** One wire per filling, no junction dots; two straight, two turning twice in one shared lane from opposite sides; arrowheads 20 px apart on the shared slot; card text and slot text on one left edge; equal 14 px padding in every frame. Agreed. |
| [block] Slots 20 px, chips and status 18 px | **System.** Slots 24, role names 22 mono, terminal 22. Agreed. |
| [polish] `pkit validate` in prose type | Monospace. |
| [polish] Empty band in the right column | The limit moved into the source line as project-kit's evidence ("each of its 3 roles has one capability so far"), and the benefits now stand on the diagram's top line, so no band is left. Differs: the verdict suggested aligning the limit with the terminal; a separate limit block would have crowded a full page, and the limit is a fact about project-kit. |
| [polish] Czech lone words in the benefits | **Engine.** The wrapper's rule; rechecked. |
| The terminal | Real `pkit status` lines for the shared slot, in their real 25-column indentation, cut by whole lines. The panel takes the full width because of that indent. |
