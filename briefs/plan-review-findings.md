# The architect's and the critic's findings on the design-first plan (8 November)

These are the findings the records of #2884, #2885 and #2886 must take into account. The full plan is `design-plan.md`, beside this file.

## Binding the design rules (architect A1, F6, F7)

- Rules bind on an artefact only where the backbone says so, and every reader takes that one answer (COR-051 point 7). A piece's content YAML is not an artefact yet, so a shipped set binds on nothing.
- Accepting the sets now is sound. The agents read the rule text only from the rule-set files, ask the backbone whether a rule binds, and report breaks as findings that inform (COR-057 point 1, "Rules that bind nothing"). When content becomes an artefact, the same findings bind, with no change to the agents.
- A loaded rule set is no way out:
  - the capability already ships `VIS`, and may ship only one loaded set (COR-070 point 1);
  - a loaded set binds a session, not an artefact, and cannot be opted out of;
  - neither `rule-set-reviewer` nor the review at the merge could read it.
- The path to binding has six steps:
  1. COR-071 is accepted (PR #2420).
  2. COR-071 is built.
  3. A core refinement lets a capability declare a data place in its working-folder location.
  4. The capability declares that place over its content files.
  5. The content schema marks its prose.
  6. The install declares a project rule set inheriting the sets, with a migration.
- Merge-gate hazard: once content binds, `rule-set-reviewer` judges the rules from YAML text without the drawn page. So word each rule so that its part judged from the text and its part only a drawn page shows come apart.

## Names (architect F8, critic gap 15)

- `VIS` is the capability's loaded set: RS-VIS-001 to 004, on the sandbox. RS-VISUAL-00N beside RS-VIS-00N will be confused, and ids are permanent (COR-051 point 3).
- Choose the design set's name before acceptance.

## The candidate rule "the form says what the content says" (architect A2, critic)

- It is the right knowledge for the pyramid's failure (Mackinlay 1986; Bertin's ordered and selective variables).
- It collides with "colour says what a thing is" (visual-communication DEC-001 point 6). An item's colour comes first from the concept it names. The five hues came from each level naming a `pkit` concept. So where a page's point is an order, the rule outranks a concept's colour. That refines DEC-001 point 6, and the record must name the refinement.
- The critic's breaking cases call for this wording:
  - a difference "a reader takes for meaning", not every difference;
  - emphasis is a difference the page's point has;
  - kinds by hue with a label, icon or shape, never hue alone (RS-VISUAL-006 as agreed);
  - order also by position or size, since shades collapse under high contrast and forced colours;
  - the layout's furniture is exempt, and the picture is judged;
  - quantity belongs in the list.
- It is partly redundant: one focal point (RS-VISUAL-001) already fails five equal bars, and DEC-001's rationale already says "a pyramid with no notation still shades its levels by their place". Its real addition is the test of a difference added or dropped.
- "A look is one system" is not a rule about pieces, since no piece can break it. It belongs to the principles of shipped brands, as a refinement of DEC-004, and not to these sets.
- The maintainer agreed the eleven rules on 31 October. Accept them as a block that cites that agreement, and take the candidate on its own.

## A piece's brief (architect A3, F5, Q2; critic gaps 4, 7, 12)

- Not in each language's content file:
  - content is what a piece shows (DEC-001 point 3);
  - a second language needs the same shape, so a brief in each would drift;
  - once content is an artefact, the brief would be marked as prose, then translated and judged by writing rules.
- Not in `piece.yaml`, which commands rewrite at every render of a draft (DEC-002 point 5).
- So: one brief per piece, in a file of its own in the piece's folder. It holds no language, and no command rewrites it. A capability schema binds it, keyed by page id, with a part for the whole piece. Its name keeps it apart from the content files. It becomes an artefact once data places exist.
- It holds what the content does not:
  - the relations the picture must show;
  - this piece's goals;
  - the takeaway, only for pages without a lead, since RS-COMM-001 makes the lead the takeaway;
  - the reasons for its design, which the maintainer asked for "behind each page, item, place, colour and font".
- The rules must not mention the brief, or the rules record would cite something a later record defines.
- A slide's fields are the slots of the deck's layouts, so a brief must work across deck, figure and site.

## The agents (architect Q3, F4; critic R2, gap 7)

- One reviewer, widened, not a second agent. Its findings stay apart by what they cite:
  - faults, as today;
  - rule findings, each citing a rule id read from the rule sets;
  - brief findings, each citing the brief's part;
  - notes on taste, which never fail.
- What a check measures stays the check's. Text-only rule parts on a diff are `rule-set-reviewer`'s. It reports and never redesigns. It checks facts against the repository (RS-COMM-005).
- The designer's method in its body: name the structure, choose the pattern by its job (the starter README's question table), choose the visual variables, then the roles. Where the library cannot draw the design: extend the library through its owner's bar, make a local component (UC-093 variant 3a), or stop, never bending the meaning.
- The designer's write scope: in an adopter, the shipped libraries are synced files the project never edits (COR-001). Where the capability is authored, its folder is the source. The overlay category must read true in both.
- The translator: "translator as fixer" contradicts the 31 October table (note, line 1082: the translator writes nothing). It leaves #2584 for #2582.
- Refinements in place in the same change, once accepted:
  - DEC-015 point 7 and the reviewer's body ("Whether a piece keeps to the rules of visual communication is not your question");
  - DEC-001's Implications;
  - DEC-002 points 1 and 5, for the brief file.

## The colour roles (critic R1; architect F2, F3)

- The foundations' roles hold six hue families of one fill, line and text each, four type roles and four spaces. No brand can give five ordered steps of one hue. Ordered shades as shared roles are an architectural change (DEC-004, DEC-001 point 6), with a record before the engine draws them. That record follows the design target (#2883's mock-ups).
- The neutral brand stays neutral: it ships to every adopter. Project-kit's identity belongs in project-kit's own libraries: the `pkit` notation, or a project-kit brand built on neutral (UC-106).
