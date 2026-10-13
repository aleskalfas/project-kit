# Records left in list form: text after the last point (#1421)

Each record below has text after its last point that is not part of that point. Converted as it stands, the text would fall into the last point's section, since a point's text runs to the next heading of the same or a higher level (COR-058 point 1). Whoever converts gives it a heading of its own, or a place in the Decision's lead (COR-058 point 9). These records stay in list form in the pull request until the maintainer decides each case.

For each case: the record, the text, the proposal, and the reason. "A heading of its own" means a sub-section of the Decision with no id, so it is no point and takes no number. Its title is new words, proposed here. "The lead" is the Decision's text before its first point. The text moves word for word in every proposal.

## Core records

### COR-028 (permission model realization)

- **The text:** "The model is authoritative; realized harness state is a generated projection of it."
- **Proposal:** the lead, as its second paragraph, after "Permissions are a harness-neutral model owned by the methodology, and each harness adapter is the realizer that enforces it."
- **Reason:** it restates the lead's claim for all four points, model over realization, and adds nothing to point 4's per-project ownership mode.

### COR-031 (capability origin)

- **The text:** the paragraph "Two further origins are **anticipated but deferred** until a concrete need arises, per the pattern-extraction discipline ([COR-007](COR-007-pattern-extraction.md)): a capability sourced from outside the kit (e.g. a private repository or local path), and the *transition* of an incubated capability into kit-shipped status (graduation). Neither has a grounded consumer today; naming them here reserves the shape without specifying mechanism." It follows D4's two bullets, a bold-label point, so the record reader takes it into D4.
- **Proposal:** the lead, after the two origins' bullets and before "The following rules apply:".
- **Reason:** it completes the lead's account of origins ("Two origins are defined now:"). D4 is about how lifecycle verbs honour origin, not about which origins exist.

### COR-039 (session repo mutation boundary)

- **The text:** "The principle is harness-neutral and universal ([COR-014](COR-014-universal-applicability.md)); the *how* — the session-anchor signal, the detection point in the CLI, the per-platform confinement story — is realization detail recorded by the permission-model realization (an ADR) and the operational discipline (a rule), not here."
- **Proposal:** the lead, after its first paragraph and before "Three properties make this real and honest:".
- **Reason:** it scopes the whole principle, what the record decides and what it leaves to an ADR and a rule. Point 3 is about the interlock's honesty only.

## Project records

### PRJ-002 (version bump policy)

- **The text:** "The changeset-file **format** and the release-step **mechanics** (changeset naming, directory, the release command's exact behaviour) are **not** fixed here — they live in the release-flow spec shipped with the implementation (#464). This record carries the *policy*; the spec carries the *mechanics*." It follows D4, a bold-label point, so the record reader takes it into D4.
- **Proposal:** a heading of its own after D4, `### Policy, not mechanics`.
- **Reason:** it says what all four points leave to the release-flow spec, so it belongs to no one point. The lead already holds the surface-change definition and the changeset rule for decisions, and is long.

### PRJ-006 (permission prompt diagnostics)

- **The text:** "The full design space, the worked report shape, and the critic/architect review outcomes are in the source scratchpad (`.pkit/scratchpad/active/2026-06-19-permissions-diagnose-prompt-loop.md`)."
- **Proposal:** the lead, after its first paragraph and before "Six sub-decisions fix the shape:".
- **Reason:** it points to the source of all six sub-decisions. Point 6 is about deferring the generic framework.
- **Also:** the path is stale. The note now lives under `.pkit/scratchpad/done/`. Mending it is a separate edit, since the conversion keeps every word.

## Capability records

### demo-recording DEC-002 (three-layer plugin architecture)

- **The text:** "Layer 1 knows nothing of Layer 2 or 3; Layer 2 knows nothing of Layer 3's vocabulary; Layer 3 depends on both. The core (Layers 1 + 2) is domain-neutral by construction."
- **Proposal:** a heading of its own after point 3, `### Knowledge flow`.
- **Reason:** it states how the three layers depend on one another, the "one-directional knowledge flow" the lead announces. It names all three layers, so in the lead it would come before the layers it names.

### project-management DEC-035 (instance ownership)

- **The text:** "This DEC **extends the `handoff-issue` contract** of [project-management:DEC-026-work-ownership-lifecycle] (new `--to-instance` modes and `--recursive`, and a same-assignee/label-only transfer mode); a reciprocal note lands on DEC-026 in the same change-set. This is a refinement-in-place, not a supersession — DEC-026's existing cross-human handoff behaviour stands."
- **Proposal:** the lead, as its second paragraph, after the paragraph that names the facility.
- **Reason:** it states the record's relation to DEC-026 for the whole facility, as the lead's first paragraph states its relation to DEC-021 and DEC-034. Point 8 is about the instance marker.

### project-management DEC-039 (containment substrate selection)

- **The text:** "The **formal** read-seam + sole-constructor contract (the consistency invariants) is pinned in a sibling architect-owned ADR (the third sibling to [ADR-026] read-path / [ADR-031] write-path); this record decides the *rule*, the ADR the *contract*." It follows D4, a bold-label point, so the record reader takes it into D4.
- **Proposal:** the lead, after its bold first paragraph.
- **Reason:** it says what the record decides and what an ADR pins, for all four points. D3 names the read-seam and D4 the render, so it is not D4's alone.

### project-management DEC-040 (multi-PR work: decline partial increment)

- **The text:** "The discriminator is the size and coupling of the increments: small steps of one unit → path 1; several real units → path 2; several units that must land together off-`main` → path 3."
- **Proposal:** a heading of its own after point 3, `### Choosing among the three`.
- **Reason:** it chooses among all three paths and names them by number, so it reads after them. Point 3 is the integration branch alone.

### project-management DEC-049 (audit journal model)

- **The text:** the paragraph "**Format + single-poster rules.** Exactly **one** audit comment per audited mutation — the underlying mutator (`move-issue`) is the sole audit-comment writer; wrappers pass the reason through rather than posting their own. **One** canonical format, sourced from a single schema field (`validation-severity.yaml`'s `audit_comment_template`), carrying a `<!-- pkit-audit -->` marker + actor + transition + reason, and — at `full` — provenance. Consistent with the existing `<!-- pkit-verdict -->` / `<!-- pkit-provenance -->` / `<!-- pkit-hook -->` markers." It follows point 3, a bold-number point, so the record reader takes it into point 3. The paragraph before it, on the drift check needing `state` carried by labels, is part of point 3.
- **Proposal:** a heading of its own after point 3, titled by its bold lead, `### Format + single-poster rules`, with the bold lead left out of its text as a point's would be.
- **Reason:** it is a rule of its own about the audit comments of point 2, with a bold lead of its own and no number. Point 3 is the governance boundary. Making it a point 4 would add a point, which the conversion does not do.
- **The methodology-reviewer's view:** agrees, and notes that moving a bold lead into the heading of a section that is no point goes slightly beyond COR-058 point 9, which describes it for points. The alternative keeps the bold lead in the text, under a heading with the same words.

### project-management DEC-050 (per-reviewer override)

- **The text:** "**[project-management:DEC-032] D3 carries the `satisfied-by-override` OR-branch** of its satisfaction predicate, and **[project-management:DEC-046] point 1 the parameterised bypass-family member**; each cites this record."
- **Proposal:** the lead, after its bold first paragraph.
- **Reason:** it names the records that carry the override, which concerns the whole record. Point 6 is the all-slots nudge.

### project-management DEC-051 (axis carriage activation)

- **The text:** two paragraphs. "**Not decided here — gate placement.** This record settles *where* an axis lives, not *when* its presence is demanded …" and "**Now decided, having been named-deferred here at first authoring.** Declaring board carriage explicitly in the map is point 2. …"
- **Proposal:** each a heading of its own after point 5. The first is titled by its bold lead, `### Not decided here — gate placement`, and the lead leaves its text. The second takes a new title, `### Board carriage declared in the map`, since its bold lead narrates the record's revision, and its text keeps that lead word for word.
- **Reason:** the first scopes the whole record. The second gives the ground for point 2, but moving it into point 2 would change that point's text. Its bold lead, and "have since been answered rather than waived", narrate the record's revision, which the decision-record specification forbids. Rewording it is a separate refinement, not part of the conversion, so the proposed title only avoids repeating the narration.

### software-engineering DEC-002 (code review panel)

- **The text:** "**Required pm-side companion decisions (cited, decided in sibling Tasks — not here):** (a) the reviewer-contribution predicate keyed on the `type` axis **plus a diff-touches-code floor**, … (b) a **per-reviewer override** … (c) an honest **`done-work` gate summary** …"
- **Proposal:** a heading of its own after point 7, titled by its bold lead without its colon, `### Required pm-side companion decisions (cited, decided in sibling Tasks — not here)`, with the bold lead left out of its text.
- **Reason:** it names decisions taken in other records, for the whole panel. Point 7 is about increment 1 being human-triggered.
- **The methodology-reviewer's view:** as for DEC-049 above.

## Architecture decision records

The architect, custodian of the ADRs (COR-025), proposes these.

### ADR-005 (permission profile surface)

- **The text:** "**Buildable scope.** This record sanctions the **minimal** profile — posture + the swappable grant-layer, with confinement and native-allow referenced/checked but not written — and fixes the fail-closed constraints point 6 places on the sandbox writer. Writing the `sandbox` block, and with it prompt-free scripting, belongs to that writer, which ADR-008 governs; drift-healing rests on managed-mode `apply` (#252), which is not built (see Implications)." It follows point 6, a bold-number point, so the record reader takes it into point 6.
- **Proposal:** a heading of its own where it stands, after point 6, `### Buildable scope`, with the text after it.
- **Reason:** it states what the whole record sanctions, and it names point 6 from outside. A heading with no id keeps it out of point 6 without moving it, as ADR-050 and ADR-064 already do.
- **Also:** ADR-008 cites ADR-005 by line, "§23", "§25" and "§27", meaning points 2, 3 and 4. Converting moves those lines (see "Records cited by line number" below).

### ADR-007 (setup command class)

- **The text:** "**First instance: `pkit permissions setup autonomy [--profile <name>]`** — composes `profile activate` (default `autonomous`), `enable`, `sandbox enable`, pauses at the restart boundary, and on the post-restart re-run executes `probe --live` and declares the goal. `pkit permissions setup autonomy down` runs `disable` + `sandbox disable` and reports the still-active model per rule 7."
- **Proposal:** a heading of its own after rule 7, `` ### First instance: `pkit permissions setup autonomy [--profile <name>]` ``. Its lead runs on into the sentence, so the paragraph keeps its bold lead and its whole sentence.
- **Reason:** the seven rules bind every instance of the setup class, and this paragraph names one instance and cites rule 7 from outside. It cannot go in the lead, which ends "The class contract, binding on every instance:" to introduce the rules, and it cites rule 7 before the rules would appear.

### ADR-039 (pkit entry point router)

- **The text:** "The **pin source** — whether the project's pin is read from `.pkit/VERSION` or from a dedicated pin file — is left to the implementation (#465) to decide and reconcile with ADR-033, not fixed here." It follows D3, a bold-label point, so the record reader takes it into D3.
- **Proposal:** a heading of its own after D3, `### The pin source`, with the sentence unchanged. The title is new, since the paragraph has no bold lead.
- **Reason:** D3 is about tags matching versions. This sentence leaves the pin input of the whole route table open, the Implications repeat it, and ADR-049 later fills it.
- **Also, its routes are points.** Routes 1 to 3, a numbered list in the lead, are cited by number throughout: "route 1/2/3" in ADR-059 (its point 4's heading among them), `src/project_kit/router.py`, `install.py`, `upgrade.py`, `tests/test_router.py`, `CONTRIBUTING.md` and `mise.toml`. So both series convert: `### 1. Source checkout → exec the in-tree dispatcher`, `` ### 2. Project pins a version ≠ me → re-exec `uvx project-kit@<pin>` ``, `### 3. Match, or no pin → run self`, then `### D1 — Version-lock soundness rests on ADR-033`, `### D2 — Graceful degradation is mandatory` and `### D3 — Pin correspondence assumes disciplined tagging`.
- **Also:** ADR-049 cites ADR-039 by line, "lines 94-95 and 155". Converting moves them.

### ADR-048 (hand-off resolve seam)

- **The text:** four paragraphs after point 2:
  - (a) "All three candidate mechanisms become implementations a binding chooses inside its `resolve`: … the seam is indifferent, and the engine stays content-free."
  - (b) "**Note on the seam analogy's limit.** …"
  - (c) "**Placement: `health` is a sibling reader module beside the engine**, in the process area's code home …"
  - (d) "**Note on the render pairing's asymmetry.** …"
- **Proposal:** two headings of their own after point 2, the text unchanged: `### The candidate mechanisms`, holding (a) and (b), and `` ### Placement: `health` is a sibling reader module beside the engine ``, holding (c) with its bold lead and whole sentence, then (d).
- **Reason:** none of the four is about what `resolve` takes and returns. (a) is the "don't pick a mechanism" half of the lead, about all three mechanisms, and (b) is about the seam as a whole. (c) is a separate decision, which `process_health.py` calls "THE PLACEMENT POINT (ADR-048, load-bearing)", and (d) qualifies it. (a) cannot go in the lead, since it names `resolve` before point 2 defines it. Making the placement a point 3 would add a point, a refinement beyond the conversion.
- **The methodology-reviewer's view:** agrees on the placement heading, but "The candidate mechanisms" fits (a) only. Either a title that covers (a) and (b), or each its own heading, such as `### The seam analogy's limit` for (b).

### ADR-049 (per-project version pin)

- **The text:** "This is **not** an ADR-039 reopening — it fills the pin-source slot ADR-039 explicitly deferred. The router's route table, loop guard, and degrade-loudly-on-unresolvable-pin posture are all unchanged."
- **Proposal:** the lead, as its second paragraph, directly after the bold summary.
- **Reason:** it states the record's relation to ADR-039 and restates the summary's last sentence, beside which it belongs. Point 7 is about dropping `--to vY`. A heading over two sentences of restatement would add structure with nothing of its own.

## Records cited by line number

Converting adds lines, so a citation that names a line of a record lands on other text afterwards. Two records whose points convert cleanly are cited that way, so they stay in list form too. Converting either means either rewriting those citations as point or section citations, which changes citations (#1421 criterion 2), or leaving them to mislead. The architect recommends rewriting them, in this change or straight after it. The converted text, as the architect confirmed it, is kept at `.agent-workspace/held-converted/`.

### ADR-004 (autonomy, intent, confinement)

- **The citations:** "ADR-004 §NN", where NN is a line of the record, from ADR-005, ADR-007, ADR-008, ADR-010, ADR-015, ADR-030, `src/project_kit/permissions.py`, `.pkit/permissions/decide.py`, `.pkit/permissions/README.md`, `.pkit/adapters/claude-code/README.md`, `.pkit/schemas/confinement-toolkit.yaml`, `tests/test_permissions_cli.py` and one scratchpad note. Converting moves every line from point 1 on by 10.
- **What each one means:** §39 is point 4. §41 is point 5. §49 is the Rationale's "Why the fail-closed invariant is a decision, not a toggle". §61 is the alternative "Relabel `network-egress`…". §63 is the alternative "Build the `pkit permissions profile` surface now". §67 is the Implications' "Issue #255 is re-scoped", and §71 their `domain-allowlist` sub-bullet. §76 is the Implications' "A future confinement preset…". ("ADR-004 §4" in `permissions.py` names point 4, and stays true.)
- **Proposal:** rewrite each as a point or section citation ("ADR-004 point 4", "ADR-004, Rationale, …"), then convert.

### ADR-002 (permission realizer ownership)

- **The citation:** "ADR-002 §26/§30" in `.pkit/adapters/claude-code/merge-settings.sh`, lines 26 and 30 of the record, which are points 1 and 2.
- **Proposal:** rewrite it as "ADR-002 points 1 and 2", then convert.

### Line citations of records that are already headed or stay as they are

- **PRJ-005** cites "COR-025 line 132" twice, for COR-025's stance against retroactive backfill. That line was already stale before this change, since the stance sits under COR-025's "No retroactive backfill" heading, and this change adds two lines to COR-025's illustrative block. It belongs in the same sweep: "COR-025, 'No retroactive backfill'".
- **ADR-008** cites ADR-005 "§23", "§25" and "§27", which are its points 2, 3 and 4, and **ADR-049** cites ADR-039 "lines 94-95 and 155". Both move when ADR-005 and ADR-039 convert (above).
- The methodology-reviewer agrees with rewriting each line citation as a point or section citation, in a commit of its own that lands no later than the record's conversion. A line number names a position, not content, so the rewrite keeps what #1421 criterion 2 protects: no citation ends up naming other content.

## Project rule 4 while records stay in list form

The pull request removes project rule 4, the interim rule that keeps every point of project-kit's records at its number until they are converted (#1399), as #1421 asks. The methodology-reviewer blocks on the timing: the rule says the conversion of project-kit's records removes it, and while the 20 records above stay in list form, a refinement may renumber their points. Several are cited by number (COR-028, COR-039, project-management DEC-035 and DEC-050, ADR-004, ADR-005, ADR-039). The removal is right once they convert in this pull request, before it merges. If the maintainer keeps any of them in list form after this pull request, rule 4 returns, narrowed to those records. The pull request's test plan carries that as an unticked box, so it cannot merge before one or the other.
