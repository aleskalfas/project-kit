# Design rationale: the four showcase pages (round 4)

Each page runs: structure → form (the alternatives weighed) → hierarchy → type → colour → space → words. Each line names the principle it rests on. The system is in `design-system.md`. What each round 3 finding led to is in `changes.md`. What the engine and libraries would need is in `gaps.md`.

**Shared brief.** The readers are developers new to pkit. The page is a 1280 × 720 slide projected in a room, a PDF handout and a web page, in English and Czech, light and dark. So: body at 24 px, nothing under 20, code at 22, no hover, and the point read in about three seconds (Duarte's glance test).

**Shared frame.** The title names the subject. The lead states the point, word for word from the brief, at 30 px in ink. The field is the evidence. The source line is one fact from project-kit itself (Alley: assertion and evidence).

**Shared colour.** One accent, green, in two forms, each with one meaning on every page (`design-system.md` section 4). *Order* is a solid fill from the ramp: a place in the chain that starts at your decisions. *Focus* is green text on the key word, with a pale tint behind a region: what the point is about. Everything else is neutral, and an outcome is an ink mark and a word (60-30-10; Albers).

---

## 1. How pkit fits together

**Structure.** An ordered stack of five, with the source on top, and three relations. Ideas enter at the top. Each layer carries out the ones above it (down). Where a layer and a decision disagree, the layer is checked first (up).

**Form: the stepped pyramid, its two relations walking the steps.**
- *Alternatives weighed.*
  - Straight diagonals, offset from the stair line (round 3). A straight line cannot be parallel to a stepped edge: its gap to the treads grows down the stack, and the reader sees perspective lines, not relations (round 3 verdict, page 1).
  - Short vertical arrows beside each note. They span no layer, which round 1's verdict failed as "decorations tied to no layer".
  - Both relations as one loop on one side. Two parallel arrows of one length cannot be told apart at a glance.
- *Chosen.* Each relation runs **16 px outside the stepped edge**, down the middle of each 32 px tread. It rounds each outer corner on an arc concentric with the level's own corner (radius 8 + 16 = 24) and goes sharp into each inner corner. So it keeps one distance from the levels all the way, measured at 16.00 px over 224 points (Gestalt continuity: the line belongs to the stack it follows). Each is anchored at both ends to the layers it relates. "Carried out" leaves the Decisions level's left side and lands on the top of the code level's tread. "If they disagree" leaves that tread on the right and lands on the Decisions level's right side. Down on the left, up on the right: together they read as one cycle around the stack. Ideas, not yet decided, sit in a dashed box sized to their words and enter the apex at its middle.

**Hierarchy.** First the title and the lead. Then the apex: the darkest, narrowest shape, where the squint test lands. Then the levels in order. Then the three notes, in semibold heads over ink-soft text. Last, the source line. Three degrees of emphasis (Refactoring UI).

**Type.** Each level's name (24 semibold) sits over its description (24 regular), centred on the pyramid's axis: flush-left text in a symmetric shape reads off balance. The notes break by phrase, by hand. The widest Czech name, "Pracovní pravidla · schémata · procesy", is checked against its level in the generator.

**Colour.** The order form: the ramp by place, deep to mid in light and pale to mid in dark (Bertin; Brewer, sequential). The levels name no concept, so the pattern shades them by place, which is visual-communication DEC-001 point 6's own example. They drop the content's five concepts because five hues would draw one order as five unrelated kinds. Also, every layer but the top holds pkit's files and yours side by side, so an ownership hue per level would be false. The arrows and the dashed box take no hue: they are relations, not things.

**Space.** The pyramid stands on the page's axis and fills the field from 224 to 606. The levels sit 8 apart: one object. *Round 4:* each column has one left edge, measured.
- The left column is the 80 px margin. The ideas box hangs on it at the top, and the "Carried out" note under it at the foot (Müller-Brockmann: few alignment edges).
- The right column is one gutter outside the base (992). Its note hangs there.
- The two notes are mirrored at the foot: each one's last line sits on the code level's last baseline (593), so the two read as a pair. Each stands beside the end of its own relation.

**Words.** The right note now says what is checked: "If they disagree / the layer is / checked first." It reads as one sentence and carries the brief's relation by itself (round 3 verdict, polish). Czech: "Když se neshodnou / kontroluje se / nejdřív vrstva.", which keeps "first" (nejdřív). Ideas: "In conversation, / or a scratchpad note." Czech takes three lines, with "ve scratchpadu" kept together.

---

## 2. Install pkit

**Structure.** A sequence of two steps: once on your machine, then in each project. Then what a project holds: pkit's files beside yours in the same folders. Then an option: keep pkit out of the repository.

**Form: the steps in order, top to bottom; the tree to the right of step 2, as its result; the option under step 2, in the same terminal notation.** Kept from round 3, which passed.
- *Alternatives weighed (round 3, unchanged).* Steps side by side would break the URL, and a broken command fails when copied. The tree under step 2 leaves room for only four lines. The tree under a prompt would claim to be output that `tree` would not print.
- *Round 4.* The option takes the `$` prompt in a panel, like the steps (round 3 verdict, polish). The same kind of thing now looks the same. It is quieter by place and label (under the steps, no number, an ink-soft label), not by notation.

**Hierarchy.** First the title and the lead. Then the two ink discs and step names, the darkest marks. Then the commands. Then the tree, whose only colour is the focus green on pkit's two entries and their tags. Then the option and the source line.

**Type.** Step names 24 semibold. Commands 22 mono: the typed text in ink, and only the prompt and the placeholder (`your-project`, Czech `vas-projekt`) muted. The tree's names are 22 mono; its tags are 24, the owner in semibold and what that means in regular.

**Colour.** *Round 4:* the focus form. pkit's entries (`core/`, `core.md`) and their tag ("pkit's, replaced") take the focus text; yours take ink. This is the page's evidence: the files an upgrade replaces. The light focus tone is lifted to L .50, so the split reads green at a glance (round 3 verdict, polish: "the page's second claim is its quietest element"). Ownership is also told by the tag's word and by its place in each pair, so colour only confirms (WCAG 1.4.1). A pale tint behind pkit's rows was weighed and refused. A band that clears its text by 12 px would overlap the next tree line at 28 px, and the tree has no room to open up.

**Space.** *Round 4:* one rhythm. 12 inside a step (disc to panel), 24 between steps, and 30 before the option, so the option stands apart from the steps (Gestalt proximity).
- Step 1's panel spans the field, because its command is the deck's longest line.
- Every panel is as wide as its longest line plus 48 (round 3 verdict, polish: step 2's half-empty panel). Step 2 holds its two real lines, `cd your-project` and `pkit init`, so its panel carries the step's weight.
- Step 2's head and the tree's head share one baseline. The tree's first line is level with step 2's panel top. The tree's last line and the option's command share one baseline (584), so the two columns start and end together.

**Words.** The Czech lead breaks by sense, one sentence a line: "Nástroj nainstalujete jednou, pak pkit přidáte do každého projektu jedním příkazem." / "Upgrade mění jen soubory pkitu, nikdy vaše." The tags echo the lead: "pkit's, replaced" and "yours, untouched".

---

## 3. Where permissions come from

**Structure.** Three kinds of permission, each through the same three stages, each ending refused for its own reason. One limit, one fact.

**Form: a flow-headed table whose last column is the evidence.**
- *Alternatives weighed.*
  - Three separate flows, one per kind: three times the arrows for one shared sequence.
  - Solid stage bars (round 3): the column labels were the heaviest ink on the page and outweighed the content (round 3 verdict, page 3).
  - Tinted outcome tiles (round 3): a second accent of equal weight that competed with the stages, and blue meant something else on page 4.
- *Chosen.* *Round 4.* Each stage is its name in semibold ink on a **2 px rule**, from the order ramp, and the rules are joined by the deck's wire. The stages read as one line with a direction, at label weight. The kinds name the rows. Each outcome is an ink no-entry mark and "Refused" in regular ink, then **the reason in semibold focus text**: the part that differs carries the weight. The eye runs down the last column and reads three different reasons (Refactoring UI: emphasise what differs).

**Hierarchy.** First the title and the lead. Then the three reasons, the page's only focus. Then the row heads and stage names in semibold ink. Then the cells, all in body ink, including column 2, the mechanism the lead names (round 3 verdict). Then the limit and the source line. Three degrees of emphasis: the reasons; the semibold heads; everything else in regular ink or quieter.

**Type.** Row heads 24 semibold, their tags 20 (furniture). Cells two lines at most, broken by phrase, by hand. Every command, tool name and agent id is mono, quoting the files as written. "Limit:" with a colon in semibold.

**Colour.** The rules take the order ramp's steps 3, 4 and 5. The stages are where the permissions live (layer 3), what pkit's commands write for the AI tool (layer 4), and the call on your work (layer 5), so the green means here what it means on page 1. The reasons take the focus form. The outcome mark is ink, with its word beside it, so the meaning never rests on colour (WCAG 1.4.1). One accent, two forms, no second hue.

**Space.** A table of a 232 px label column and three equal stages of 264, with 32 gutters (equal stages, because the stages are equals).
- *Round 4:* every cell's text hangs on its column's edge, which is the stage name's and the rule's edge: one alignment for the whole table (round 3 verdict: two alignment logics).
- Rows run 88 apart on two shared baselines, 34 px between rows.
- The limit has its own band. A 2 px keyline divider runs across the table, and the limit's cap height sits 54 px under the last row's text, against 34 between rows (Gestalt proximity: a page-wide caveat is a separate group).

**Words.** The reasons are one line each: "in every mode", "any tool not listed", "uses pkit's commands". The data cells quote the real deny list and the real agent file. The fact: 14 denies and 62 allows, counted in the project's `.claude/settings.json`.

---

## 4. How capabilities work together

**Structure.** One capability plays a role and opens three slots under it. Two other capabilities, each in its own role, fill those slots. Evidence: what `pkit status` prints for the shared slot. What it gives you: three short benefits. The limit: one capability per role so far.

**Form: the role as a container of its slots; the fillers wired into the slots; the proof under it; the benefits beside it.**
- *Alternatives weighed.*
  - Round 3's grey blocks with role tags and sockets. The role was the quietest element, the arrows ran from capability to capability, and every kind shared one 1.15:1 grey (round 3 verdict, page 4: blocking).
  - Slots as sockets cut into an edge. The opening read as a shift, not a socket, and a cut-out needs a second stroke logic.
  - The role as a free label above project-management. It would name the role without making it the thing the arrows land on.
- *Chosen.* *Round 4.* **The role is the container.** Its heading reads "Role `pkit::work-tracking`", and the capability that plays it sits second: "project-management opens 3 slots". So a reader sees at a glance which capability, in which role, opens three slots. Under the heading, the **slots are compartments, wall to wall**: `doc-check`, `fixers`, `use-cases`, each with what it holds. A wire that lands on the container's wall at a slot's row lands on that slot (Mackinlay: the form expresses the structure). The fillers take the same form in small, role over name: `pkit::documentation` over living-docs, `pkit::analysis` over software-analysis. So "a capability in its role" looks the same wherever it stands (Gestalt similarity). "Role" and "slot" are each named once in the drawing, in the lead's words.
- *Wires.* Each filler sits level with the slot only it fills, so that wire is straight. Its wire to the shared `fixers` slot leaves 10 px from its middle, turns twice on the deck's radius, and lands on `fixers`, mirrored with the other filler's. No wires cross.
- *The proof.* The real `pkit status` lines for `fixers`, cut by whole lines and dedented together, in the deck's terminal under the diagram. The two `bound` lines take the focus tint, as the `fixers` row does, and `fixers` is the focus word in both places. The link from slot to proof is carried by the one form (Gestalt similarity), which round 3's verdict called the page's best idea.

**Hierarchy.** First the title and the lead. Then the role container: its 2 px outline is the page's strongest boundary, and its heading is the only semibold word in the diagram. Then the `fixers` row in focus, then its proof. Then the fillers and the benefits, then the caption and the source line.
- *Round 4:* one level for the role (mono ink) and a quieter one for the capability (sans ink-soft), in the container and in both fillers alike. The role outranks the name because the page's point is that capabilities see only roles.
- The benefits have a head, "What it gives you", and are set in ink. The caption is a caption: 20 px muted, level with the lines it names (round 3 verdict: same grey style for different kinds).

**Type.** Role and slot ids in mono 22 ink. Capability names in the sans 24 ink-soft. Slot purposes in 24 ink. "Role" in semibold. `pkit validate` and `pkit status` in mono 22 inside 24 px text.

**Colour.** Neutral, with one focus. *Round 4:* the containers are a 2 px outline at 4.3 to 1 on the paper, both modes (WCAG 1.4.11; round 3's were 1.5). The terminal is the panel fill with no line, as on page 2, so a terminal and a capability no longer look alike (Bertin: different kinds, different looks). The focus marks only the slot that is proven and the lines that prove it (60-30-10).

**Space.** Two columns: 854 (the terminal's real line, and the diagram above it) and 234, with the 32 px gutter.
- The fillers (299 px) and the container start on the evidence column's two edges, 80 and 427, with a 48 px lane for the wires between them.
- The upper filler's top is level with the container's heading divider, and the lower filler's bottom with the container's foot.
- *Round 4:* every container sets its text 24 px from its left side, measured. The `fixers` tint clears its text by 12.7 px, and the status band clears the line above it and the lines inside it by 12.0 (round 3 verdict: 3 and 4 px). All lines are 2 px.
- The note column starts on the field's top. The caption's first baseline is level with the first `bound` line, so the caption sits beside what it names (Mayer: spatial contiguity).

**Words.** The benefits stand as three two-line items under their head. The caption names the command: "What `pkit status` prints for this slot." The limit is the source line, a fact about project-kit: "each of its 3 roles has one capability so far, so a swap is designed, not yet shown."
