# Text after the last point, sorted into rules and notes (#1421)

A decision record lists its decisions as numbered points. Pull request #1569 rewrites each point as a heading of its own, so that its number stays fixed for good (COR-058). This is called *converting* the record. A record whose points are still a numbered list, or paragraphs opening with a bold number, is in *list form*.

Eighteen records stayed in list form in #1569, because some text follows their last point. Converted as they stand, that text would read as part of the last point. On 13 October the maintainer decided how such text is placed:

- **A rule** is text that decides something the record holds: what must or must not happen, how to choose, or where a thing lives. It becomes **the record's next numbered point**. It takes the next number the record has not used (COR-058 point 3), so no existing point changes its number.
- **A note** is text about the record's scope or about other records: what the record does not decide, where its design lives, how it relates to another record, or a repeat of what the record already says. It gets **a heading of its own with no number**, or moves into **the Decision's opening**.

In every case the words stay as they are. Only a heading's title is new text.

Some words used below:

- **A point** is one numbered decision of a record, such as point 4. Once the record is converted, each point is a heading like `### 4. Title`, and other records cite it as "point 4". Some records name their points with a label instead of a bare number, such as D3, and keep those labels. ADR-007 calls its points "rules", so its point 7 is "rule 7".
- **A heading of its own** is a sub-heading inside the Decision with no number. It is no point, so nothing can cite it by number. It only stops the text from being read as part of the point above it.
- **The opening** is the Decision's text before its first point.
- **A bold lead** is the bold words a paragraph starts with, such as "**Buildable scope.**". When a paragraph becomes a point, its bold lead becomes the point's title and leaves the text (COR-058 point 9). This list proposes the same for a note's heading. The other way would keep the bold lead in the text too, with the heading repeating it; the maintainer may prefer that. A bold lead that runs on into its sentence always stays in the text, so the sentence still reads. One that would make a misleading title stays in the text, and the heading gets a new title.

## The sorted list

| Record | Rule or note | Where it goes | New heading |
|---|---|---|---|
| COR-028 | note | the opening, second paragraph | none |
| COR-031 | note | the opening, after the two origins | none |
| COR-039 | note | the opening, after its first paragraph | none |
| PRJ-002 | note | after D4 | `### Policy, not mechanics` |
| PRJ-006 | note | the opening, after its first paragraph | none |
| demo-recording DEC-002 | **rule** | point 4, after point 3 | `### 4. One-directional knowledge flow` |
| project-management DEC-035 | note | after point 8 | `### How this record extends DEC-026` |
| project-management DEC-039 | note | the opening, after its bold first paragraph | none |
| project-management DEC-040 | note | after point 3 | `### Choosing among the three` |
| project-management DEC-049 | **rule** | point 4, after point 3 | `### 4. Format + single-poster rules` |
| project-management DEC-050 | note | after point 6 | `### The records that carry the override` |
| project-management DEC-051, first paragraph | note | after point 5 | `### Not decided here — gate placement` |
| project-management DEC-051, second paragraph | note | after the first | `### Why board carriage can be declared` |
| software-engineering DEC-002 | note | after point 7 | `### Required pm-side companion decisions (cited, decided in sibling Tasks — not here)` |
| ADR-005 | note | after point 6 | `### Buildable scope` |
| ADR-007 | note, **an exception for the maintainer to confirm** | after rule 7 | `` ### First instance: `pkit permissions setup autonomy [--profile <name>]` `` |
| ADR-039 | note | after D3 | `### The pin source` |
| ADR-048, paragraph (a) | **rule** | point 3, after point 2 | `### 3. The binding chooses the mechanism` |
| ADR-048, paragraph (b) | note | after point 3 | `### Note on the seam analogy's limit` |
| ADR-048, paragraphs (c) and (d) | **rule** | point 4, after that note | `` ### 4. Placement: `health` is a sibling reader module beside the engine `` |
| ADR-049 | note | the opening, second paragraph | none |

**The count.** Of the 18 records, 3 gain new points: demo-recording DEC-002, project-management DEC-049, and ADR-048, which gains two. That makes 4 new points. The other 15 records hold notes only. Counted by paragraph, 5 paragraphs go into points (ADR-048's (d) rides in its point 4) and 17 stay notes.

**What changed from the first list** (the proposal the maintainer read before deciding the rule, `review/trailing-text-1421.md`):

- Five paragraphs that the first list gave a heading of their own now go into points: those of demo-recording DEC-002 and project-management DEC-049, and ADR-048's (a), (c) and (d).
- ADR-048's (b) now has a heading of its own, instead of sharing one with (a).
- project-management DEC-035 and DEC-050 move from the opening to a heading of their own after their last point. Each names things that a later point defines, so in the opening it would come before them. That is the reason the first list kept demo-recording DEC-002 and ADR-048's (a) out of the opening, and it now applies to all four alike.
- project-management DEC-051's second paragraph gets a title that matches its content.
- Every other note keeps the first list's proposal.

**Two cases where the project manager expected a rule** are notes here. project-management DEC-040 repeats its points 1 to 3. ADR-007's paragraph is an exception, which the architect asks the maintainer to confirm.

## Core records

### COR-028 (permission model realization)

> The model is authoritative; realized harness state is a generated projection of it.

- **Note.** It repeats what point 1 and the opening already say, that the model is the source of truth and each harness only carries it out, and decides nothing new.
- **Where:** the opening, as its second paragraph, after "Permissions are a harness-neutral model owned by the methodology, and each harness adapter is the realizer that enforces it." As in the first list.

### COR-031 (capability origin)

> Two further origins are **anticipated but deferred** until a concrete need arises, per the pattern-extraction discipline ([COR-007](COR-007-pattern-extraction.md)): a capability sourced from outside the kit (e.g. a private repository or local path), and the *transition* of an incubated capability into kit-shipped status (graduation). Neither has a grounded consumer today; naming them here reserves the shape without specifying mechanism.

- **Note.** It names two origins the record leaves undecided. That is the record's scope, not a rule.
- **Where:** the opening, after the bullets of the two origins and before "The following rules apply:". It completes the opening's "Two origins are defined now:". As in the first list.

### COR-039 (session repo mutation boundary)

> The principle is harness-neutral and universal ([COR-014](COR-014-universal-applicability.md)); the *how* — the session-anchor signal, the detection point in the CLI, the per-platform confinement story — is realization detail recorded by the permission-model realization (an ADR) and the operational discipline (a rule), not here.

- **Note.** It says what the record leaves to an ADR and to a rule, for the whole principle.
- **Where:** the opening, after its first paragraph and before "Three properties make this real and honest:". As in the first list.

## Project records

### PRJ-002 (version bump policy)

> The changeset-file **format** and the release-step **mechanics** (changeset naming, directory, the release command's exact behaviour) are **not** fixed here — they live in the release-flow spec shipped with the implementation (#464). This record carries the *policy*; the spec carries the *mechanics*.

- **Note.** It says what the record does not fix, and where that is fixed instead, for all four points.
- **Where:** a heading of its own after D4, `### Policy, not mechanics`. The opening is already long and holds the definitions. As in the first list.

### PRJ-006 (permission prompt diagnostics)

> The full design space, the worked report shape, and the critic/architect review outcomes are in the source scratchpad (`.pkit/scratchpad/active/2026-06-19-permissions-diagnose-prompt-loop.md`).

- **Note.** It says where the record's design work lives.
- **Where:** the opening, after its first paragraph and before "Six sub-decisions fix the shape:". As in the first list.
- **Follow-up, outside #1569:** the path is stale. The note now lives under `.pkit/scratchpad/done/`.

## Capability records

### demo-recording DEC-002 (three-layer plugin architecture)

> Layer 1 knows nothing of Layer 2 or 3; Layer 2 knows nothing of Layer 3's vocabulary; Layer 3 depends on both. The core (Layers 1 + 2) is domain-neutral by construction.

- **Rule.** It decides which layer may depend on which, a direction the opening only names as "one-directional knowledge flow". Points 1 to 3 say what each layer knows, but not that Layer 3 depends on both others while neither depends on it. The record's Rationale defends it as a decision ("It is not a style preference").
- **Where:** point 4, after point 3. The record has points 1 to 3, so 4 is the next number.
- **Title:** `### 4. One-directional knowledge flow`, the words the opening and the Rationale use. The paragraph has no bold lead, so the title is new text.

### project-management DEC-035 (instance ownership)

> This DEC **extends the `handoff-issue` contract** of [project-management:DEC-026-work-ownership-lifecycle] (new `--to-instance` modes and `--recursive`, and a same-assignee/label-only transfer mode); a reciprocal note lands on DEC-026 in the same change-set. This is a refinement-in-place, not a supersession — DEC-026's existing cross-human handoff behaviour stands.

- **Note.** It states how the record relates to DEC-026. The new hand-off modes it names are decided in point 4.
- **Where:** a heading of its own after point 8, `### How this record extends DEC-026`, new text. **This changes the first list**, which put it in the opening. It names the `--to-instance` modes and the transfer between one person's own copies, which point 4 defines. In the opening, a reader would meet them before point 4.

### project-management DEC-039 (containment substrate selection)

> The **formal** read-seam + sole-constructor contract (the consistency invariants) is pinned in a sibling architect-owned ADR (the third sibling to [ADR-026] read-path / [ADR-031] write-path); this record decides the *rule*, the ADR the *contract*.

- **Note.** It says what an ADR decides instead of this record.
- **Where:** the opening, after its bold first paragraph. As in the first list.

### project-management DEC-040 (multi-PR work: decline partial increment)

> The discriminator is the size and coupling of the increments: small steps of one unit → path 1; several real units → path 2; several units that must land together off-`main` → path 3.

- **Note.** It repeats the choice that points 1 to 3 already make. Each of those points opens with when to use it: "small steps of a single PR-sized unit", "genuinely several PR-sized units", "several Tasks must assemble off-`main`". The sentence says the same again in short. Its only new words name what the choice turns on, "size and coupling". The record's Implications repeat the same choice a third time. As a point, it would put the rule in two points, and a later change to one path's condition would have to edit both.
- **Where:** a heading of its own after point 3, `### Choosing among the three`, new text. As in the first list.
- **The methodology reviewer** blocked this as a rule, for the reason above.

### project-management DEC-049 (audit journal model)

> **Format + single-poster rules.** Exactly **one** audit comment per audited mutation — the underlying mutator (`move-issue`) is the sole audit-comment writer; wrappers pass the reason through rather than posting their own. **One** canonical format, sourced from a single schema field (`validation-severity.yaml`'s `audit_comment_template`), carrying a `<!-- pkit-audit -->` marker + actor + transition + reason, and — at `full` — provenance. Consistent with the existing `<!-- pkit-verdict -->` / `<!-- pkit-provenance -->` / `<!-- pkit-hook -->` markers.

- **Rule.** It decides how many audit comments a change posts, which command alone posts them, and their one format. No other point says this, and DEC-050 point 4 relies on that format.
- **Where:** point 4, after point 3. The paragraph before it, on the drift check needing `state` carried by labels, stays in point 3.
- **Title:** `### 4. Format + single-poster rules`, from its bold lead, which leaves the text as any point's does (COR-058 point 9).

### project-management DEC-050 (per-reviewer override)

> **[project-management:DEC-032] D3 carries the `satisfied-by-override` OR-branch** of its satisfaction predicate, and **[project-management:DEC-046] point 1 the parameterised bypass-family member**; each cites this record.

- **Note.** It names the other records that carry this one's override. What they carry is decided in points 1 and 2.
- **Where:** a heading of its own after point 6, `### The records that carry the override`, new text. **This changes the first list**, which put it in the opening. "`satisfied-by-override`" is defined in point 2 and "the parameterised bypass-family member" in point 1. In the opening, a reader would meet both before they are defined.

### project-management DEC-051 (axis carriage activation)

First paragraph:

> **Not decided here — gate placement.** This record settles *where* an axis lives, not *when* its presence is demanded or who pays when a predecessor omitted it. Those are a separate question, open and tracked: completeness is enforced today at filing and editing only, the Todo→Backlog doorway validates nothing, and an issue that never came through this capability is asked nothing at all. Nothing in this record should be read as settling that.

- **Note.** It says what the record does not decide.
- **Where:** a heading of its own after point 5, `### Not decided here — gate placement`, from its bold lead, which leaves the text. As in the first list.

Second paragraph:

> **Now decided, having been named-deferred here at first authoring.** Declaring board carriage explicitly in the map is point 2. The deferral's ground was that an axis is not *gate-verified* on the board — the read path and its failure semantics unsettled — and shipping the arm before then would let an adopter declare a substrate the gate cannot check. Both halves of that ground have since been answered rather than waived. The read exists and is careful: a board field's current value is read through a query that trusts only a positively-confirming response and treats every other shape as unread. And the failure semantics are now ruled: an unreadable board **raises an error**, scoped to projects that actually expect a value from a board, because a board that will not answer is a broken tool rather than a missing value — distinct from a board that answers *unset*, which is a separate question about missing values. Those semantics are a read-path contract rather than a precedence rule, so they are recorded architecture-side in their own record, not here.

- **Note.** It gives the reasons point 2 can be decided, and says the error rule it mentions is decided in an architecture record, "not here". The rule itself is point 2.
- **Where:** a heading of its own after the first paragraph, `### Why board carriage can be declared`, new text. The paragraph keeps its bold lead, which tells the record's history and would make a misleading title. **The title changes the first list's** `Board carriage declared in the map`, which named point 2's decision rather than this paragraph's reasons.
- **Follow-up, outside #1569:** the bold lead and "have since been answered" tell the record's history, which the decision-record specification forbids in a record. So does point 3's "An earlier draft … Withdrawn". Rewording them is a refinement of its own. The conversion keeps the words.

### software-engineering DEC-002 (code review panel)

> **Required pm-side companion decisions (cited, decided in sibling Tasks — not here):** (a) the reviewer-contribution predicate keyed on the `type` axis **plus a diff-touches-code floor**, so the panel activates on any code-carrying PR regardless of the closing issue's classification (closes #715's mislabeled/unclassified escape); (b) a **per-reviewer override** — override one agent's block with an audited reason, without discarding the whole gate; (c) an honest **`done-work` gate summary** enumerating which perspectives reviewed and any required-but-missing one.

- **Note.** It names decisions taken in other records ("not here").
- **Where:** a heading of its own after point 7, titled by its bold lead without the colon, with the bold lead left out of the text. As in the first list.

## Architecture decision records

The architect, custodian of the ADRs (COR-025), confirmed ADR-005, ADR-039, ADR-048 and ADR-049 as below. For ADR-007 it judged the paragraph a note, where this sorting had first read it as a rule.

### ADR-005 (permission profile surface)

> **Buildable scope.** This record sanctions the **minimal** profile — posture + the swappable grant-layer, with confinement and native-allow referenced/checked but not written — and fixes the fail-closed constraints point 6 places on the sandbox writer. Writing the `sandbox` block, and with it prompt-free scripting, belongs to that writer, which ADR-008 governs; drift-healing rests on managed-mode `apply` (#252), which is not built (see Implications).

- **Note.** It says what the whole record allows to be built, and what it leaves to ADR-008. The rules it sums up are points 2 and 6.
- **Where:** a heading of its own where it stands, after point 6, `### Buildable scope`, from its bold lead, which leaves the text. As in the first list.

### ADR-007 (setup command class)

> **First instance: `pkit permissions setup autonomy [--profile <name>]`** — composes `profile activate` (default `autonomous`), `enable`, `sandbox enable`, pauses at the restart boundary, and on the post-restart re-run executes `probe --live` and declares the goal. `pkit permissions setup autonomy down` runs `disable` + `sandbox disable` and reports the still-active model per rule 7.

- **An exception, placed as a note.** The paragraph does decide things: which commands the first setup command runs, its default profile, and what its `down` form runs. By the maintainer's rule that would make it point 8. The architect asks that it stay a note, and that it become point 8 only on the maintainer's explicit word.
- **Why a note.** The record decides a *class* of setup commands. Its numbered points are the class's rules, which bind every setup command. The opening introduces them as "The class contract, binding on every instance:", other records cite them as "rule 2", "rule 6" and so on, and the Implications count "seven rules". This paragraph binds no other setup command, so as point 8 it would be the one point of that series that is no rule of the class. It says what accepting the record let be built, as ADR-005's "Buildable scope" does, which is a note.
- **What the later records show.** Four later records changed what the command runs: ADR-008, ADR-010, ADR-027 and ADR-028. Each says ADR-007's contract is unchanged, and none says it changes ADR-007. They treat this paragraph as a description of the command when the record was accepted. As a point, it would be cited as a decision of ADR-007 that those records changed without saying so.
- **Where:** a heading of its own after rule 7, as in the first list. It cites rule 7, so it must come after it.
- **Title:** `` ### First instance: `pkit permissions setup autonomy [--profile <name>]` ``, from its bold lead. The bold lead runs on into its sentence, so the paragraph keeps it and stays whole. The code cites it as "ADR-007 first instance", which the heading keeps true.
- **Follow-up, outside #1569:** ADR-007 could point to the four later records, since its first-instance text no longer says everything the command runs.

### ADR-039 (pkit entry point router)

> The **pin source** — whether the project's pin is read from `.pkit/VERSION` or from a dedicated pin file — is left to the implementation (#465) to decide and reconcile with ADR-033, not fixed here.

- **Note.** It says what the record leaves open, which ADR-049 later decides.
- **Where:** a heading of its own after D3, `### The pin source`, new text. As in the first list.
- **Also, as in the first list:** the record's opening holds a numbered list of three routes, and other records and code cite them as "route 1", "route 2" and "route 3". So those convert too, as points 1 to 3, before D1 to D3.

### ADR-048 (hand-off resolve seam)

This record is about how one process checks that another process picked up its work. In its words, a *binding* is the part a project writes for its own processes. The *engine* is the shared code that runs every process. `resolve` (point 2) is the step a binding supplies to find the item downstream that matches one upstream item. Four paragraphs follow point 2, and each is placed on its own.

(a)

> All three candidate mechanisms become implementations a binding chooses inside its `resolve`: a naming template (derive the downstream id and check existence), a scan of the binding's own declared artifact root (e.g. grep unit files for the screen binding), or a maintained mapping if a binding insists on one — the seam is indifferent, and the engine stays content-free.

- **Rule.** It is the "don't pick a mechanism" half of the record's bold summary. It decides that how a downstream item is found is the binding's choice, made inside `resolve`, and never the engine's. It also allows all three ways, including a maintained mapping, which the Rationale rejects only as the one way for every project.
- **Where:** point 3, after point 2.
- **Title:** `### 3. The binding chooses the mechanism`, new text, since the paragraph has no bold lead.

(b)

> **Note on the seam analogy's limit.** This is the *shape* of cascade's seam, not the same seam. Cascade's per-candidate confirm is a **binding-supplied** `membership` test; health's confirm is the **engine's own** at-exact-state position read. That choice is what hard-codes COR-042's live at-the-trigger snapshot (and its ephemeral-trigger consequence) at the mechanism level — deliberately: it keeps confirmation deterministic and engine-owned, and one seam predicate fewer for bindings to write. The rejected symmetric alternative is below. The crossing this machinery constitutes is sanctioned by COR-042 (its "second bounded cross-subject read" section); the discipline — binding-supplied sources, per-subject confirmation, point-to-point resolution, no listing API — holds in the same form COR-037's seam established.

- **Note.** It compares this design with a similar one in another record, and explains a choice point 1 already makes: the engine, not the binding, confirms each candidate.
- **Where:** a heading of its own after point 3, `### Note on the seam analogy's limit`, from its bold lead, which leaves the text. **This changes the first list**, which put (a) and (b) under one heading whose title fitted (a) only.

(c)

> **Placement: `health` is a sibling reader module beside the engine**, in the process area's code home next to the render — not inside the engine's runtime paths. It reads process definitions for `depends_on` contracts, calls the two seam predicates, and calls the engine's public per-subject position resolution for confirmation. The runtime operations' code paths (`status` / `can-move` / `move` / `validate`) import nothing from it and never read `depends_on` — keeping COR-042's re-scoped reader-set claim structurally true by module boundary, not by convention.

(d)

> **Note on the render pairing's asymmetry.** COR-042 pairs `health` with the graph render as out-of-runtime readers, but they are different kinds of reader: the render reads *declarations only* — never a live position, never a predicate, never the engine (its safety pin, asserted by its tests). `health` **does** read live reality — positions via the engine, plus two binding predicates — and is safe by **report-only**, not by never-reading. The module-boundary claim above gets the same pinned treatment the render got: a test asserting the runtime operation paths import nothing from the health module.

- **Rule.** (c) decides where the code of the `health` check lives, and that the engine's everyday commands never use it. The code calls this "THE PLACEMENT POINT (ADR-048, load-bearing)". (d) belongs to the same point. It explains why that placement is safe, and its last sentence requires the test that holds the separation, which `tests/test_process_health.py` carries. Under a heading of its own, (d) would take that requirement out of the point it enforces.
- **Where:** point 4, holding (c) and then (d), after the note on (b).
- **Title:** `` ### 4. Placement: `health` is a sibling reader module beside the engine ``, from (c)'s bold lead. That lead runs on into its sentence, so it also stays in the text. (d) keeps its own bold lead inside the point.

### ADR-049 (per-project version pin)

> This is **not** an ADR-039 reopening — it fills the pin-source slot ADR-039 explicitly deferred. The router's route table, loop guard, and degrade-loudly-on-unresolvable-pin posture are all unchanged.

- **Note.** It states how the record relates to ADR-039, and repeats the last sentence of the bold summary ("ADR-039 stays closed").
- **Where:** the opening, as its second paragraph, directly after the bold summary. As in the first list.

## Also kept from the first list

- **Citations by line number.** Some records cite a passage of another record by its line number, such as "ADR-004 §39". Converting adds lines, so such a citation would land on other text. They are rewritten as point or section citations ("ADR-004 point 4"), in a commit that lands no later than the cited record's conversion. This concerns ADR-004, ADR-002, ADR-005, ADR-039 and COR-025.
- **Project rule 4** keeps every point of project-kit's records at its number until they are converted. #1569 removes it. If any of these records is still in list form when #1569 merges, the rule returns for those records.
- **New points pass the numbering check.** A new point is added while its record is converted, under the next unused number. The numbering check (COR-058 point 8) fails nothing for a new number past the record's highest.
