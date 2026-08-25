---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-26
---

# Core evolution timeline

## Narrative arc

project-kit's core evolves in four discernible eras, each building on the last, and the whole corpus is held together by one meta-discipline — extract on recurrence, never on anticipation (COR-007) — applied recursively to the methodology itself.

**Era 1 — Foundations: the mechanism layer (COR-001..010, early–mid May 2026).** The corpus opens by grounding the pre-existing no-shared-files invariant in operational terms: exactly three content mechanisms (propagation / extension / suspension) plus delivery operations (seed, then merge). From that base it derives, in tight succession, how mechanisms map to artifact types, the CLI surface that invokes them, the bundle/adapter pattern for alternatives, the five content-artifact roles, the extract-on-recurrence principle, git and PR conventions, and the two-tier versioned lifecycle with migrations. This era answers "how does core content reach and coexist with a project, and how does it version?"

**Era 2 — Structure matures: areas, agents, capabilities, schemas (COR-011..020, May 2026).** Once the mechanisms exist, the corpus names the containers. Areas become first-class; scratchpad notes become a fifth content shape; agents get a full architecture (references-in-frontmatter, hooks, overlays); the universal-applicability test is generalised across all artifact kinds; flat-vs-folder layout, storyboards, and — the pivotal move — the **capability** as an opt-in installable discipline arrive, with schemas as capabilities' engine-data layer. This era answers "what are the reusable units of methodology, and how do adopters opt into disciplines?"

**Era 3 — The capability ecosystem hardens (COR-021..031, late May–June 2026).** With capabilities established, the corpus makes them operable: command dispatch, adopter-data schema binding (COR-022 superseded by COR-023 within days — a fast self-correction), the critic/architect reviewer roles, the ADR decision space, agent-placement-by-discipline, the retirement of the never-used bundle pattern (COR-027 supersedes COR-005's bundle half), adapter-realized permissions, cross-file data references, capability dependencies, and capability origin. This era answers "how do disciplines compose, review, and depend on each other safely?"

**Era 4 — The process substrate (COR-032..044, June–August 2026).** The largest single arc: a content-free state-machine engine (COR-033) that capabilities bind process definitions to, with position inferred from reality and gates an actor cannot talk past. COR-033 deliberately names its variation axes and ships only a grounded core; the following records then *un-defer one slot at a time, each on a real binding* — keyed subjects, blocked waits, invariants, composition, cascade, connections, open regions, health checks — culminating in an authoring layer (COR-044) that splits a definition's declarative *shape* (a skill) from its domain-logic *teeth* (an owner-scoped agent). Interleaved are the cross-repo mutation boundary (COR-039) and external-source distribution (COR-041).

**The throughline.** Every era is the same disposition applied at a new altitude: name the durable principle, keep inventory out of the record, ship the minimal grounded thing, and un-defer named slots only when a second real consumer proves the shape. The methodology is built the way it tells adopters to build — principles over inventory, recurrence over anticipation, one owner per file, honesty about what a mechanism cannot do.



## Timeline

_Dates are the frontmatter `date` (authored date). Git history only begins 2026-06-13 (the public import), so commit dates are not the authored dates._

### Foundations — the mechanism layer (COR-001..010)

**COR-001 — Content mechanisms** · 2026-05-01
- **Motivation:** The no-shared-files invariant says *who* owns each file but not *how* canonical core content reaches projects, how projects add content alongside, or how they override where allowed.
- **Key thinking / rejected alternatives:** Exactly three steady-state mechanisms — propagation, extension, suspension — plus install-time seeding as a one-time delivery *operation*, not a fourth mechanism. Rejected: four mechanisms with stamping as a peer; folding suspension into extension; a single unified mechanism with metadata flags (creates a second authority competing with file location).
- **Builds on / produced by:** Foundational; grounds the no-shared-files invariant in operational terms.

**COR-002 — Merge delivery operation for adopter config files** · 2026-05-04
- **Motivation:** Fixed-path adopter config files (permissions, gitignore, hooks) need structured delivery: core has a growing baseline it wants present, but the adopter has their own entries that must survive. Pure propagation overwrites; pure seeding never updates.
- **Key thinking / rejected alternatives:** Adds *merge* as a second delivery operation (re-runnable, baseline + project-additions), distinct from one-shot seeding.
- **Builds on / produced by:** COR-001 (extension + seeding); explored in the `example-brownfield` walk (2026-05-04-inventory).

**COR-003 — Mechanism assignment for artifact types** · 2026-05-05
- **Motivation:** COR-001/002 give the mechanisms but not *how a maintainer chooses* one for a given artifact, nor which cross-cutting principles govern the choice.
- **Key thinking / rejected alternatives:** Ships *principles*, not a path-by-path map (an inventory would force an amendment per file added). Names the normativity-suspendability line (decisions/rules/methodology may not be suspended; agents/scripts may) and keeps runtime deployment off the mechanism list. Rejected: pinning the current path map inside the record.
- **Builds on / produced by:** COR-001, COR-002; also establishes the two-namespace `core/`+`project/` pattern later reused everywhere.

**COR-004 — CLI command surface** · 2026-05-05
- **Motivation:** Nothing yet said *how a project invokes* the mechanisms, or the design rules for the CLI exposing them.
- **Key thinking / rejected alternatives:** Principles not the command list; anchor each command to one operation (sync = propagation, merge = merge) so verbs mirror the mechanism vocabulary and consent contracts stay legible; first-install is sharp not smart (recovery pushed into `validate`). Rejected: a smart `update` verb that picks sync/merge/migration (conflates consent profiles); transactional rollback.
- **Builds on / produced by:** COR-001, COR-002, COR-003; defers binary name/language/channel to PRJ records.

**COR-005 — Bundle and adapter pattern** · 2026-05-05
- **Motivation:** The two-namespace pattern fits *universal* areas (one canonical version) but not two other shapes: bundle-based areas (many backends implementing one contract, e.g. issue trackers) and harness-flavoured content (Claude Code, Codex, Cursor).
- **Key thinking / rejected alternatives:** `bundles/` are area-internal, `adapters/` are top-level (adapters cut across areas); install signal is presence of `project/<name>/` (no second source of truth); authoring is on the public surface via scaffold commands, and every authoring command is paired with a skill (the script stamps, the skill carries the disciplines). Rejected: `installed/` peer, `installed.yaml`, `enabled:true` flags, adapters-as-bundles, skills-only or commands-only.
- **Builds on / produced by:** COR-003 (two-namespace pattern); the command/skill pairing rule anchors COR-020 and the authoring-skill regime.

**COR-006 — Roles of content artifacts** · 2026-05-05
- **Motivation:** Content arrives in five shapes (decisions, docs, skills, agents, scratchpad notes) whose boundaries blur; without a rule, the same guidance drifts across artifact types.
- **Key thinking / rejected alternatives:** One placement rule — decisions carry *why*, docs *what-is*, skills *procedure*, agents *role*, scratchpad *what-might-become*; skills/agents cite rather than embed (cited content never goes stale); harness-agnostic. Rejected: folding skills/agents into docs; letting decisions carry procedure "when really part of the decision."
- **Builds on / produced by:** Sibling to COR-007 (the extract/carrier split); the discriminator both records use.

**COR-007 — Extract recurring patterns into tooling** · 2026-05-05
- **Motivation:** A methodology's value compounds only when recurring shapes of work are distilled into tooling; otherwise wisdom stays as founders' folklore.
- **Key thinking / rejected alternatives:** Trigger is *recurrence*, not anticipation (premature abstraction locks in guesses); the carrier choice belongs to COR-006, not here; the principle is named recursively (it applies to itself). Rejected: implicit disposition; a hard "extract on second occurrence" rule; limiting it to skills.
- **Builds on / produced by:** Pairs with COR-006 (should-we-extract vs what-carrier).

**COR-008 — Git workflow conventions** · 2026-05-05
- **Motivation:** Adopting projects do source-control work; without conventions, every author picks their own format and history resists automation.
- **Key thinking / rejected alternatives:** Two *universal* (platform-independent) conventions — conventional commits + commit-per-logical-unit — with a project-extensible type vocabulary (`decision:` etc.). Rejected: no convention; a custom format; strict conventional-commits with no extensions; multi-purpose commits.
- **Builds on / produced by:** Platform-specific PR layer split out to COR-009.

**COR-009 — Pull-request workflow conventions** · 2026-05-05
- **Motivation:** COR-008's git conventions are platform-independent; projects on PR-based platforms need the layer covering how a branch becomes a change on the default branch.
- **Key thinking / rejected alternatives:** Default squash-merge (linear history, trivial revert, reliable bisect), PR title load-bearing (squash derives its subject from it), short-lived branches, PRs recommended not enforced (solo-work friction). Rejected: merge-commit/rebase-merge defaults; per-PR merge style; mandating PRs always.
- **Builds on / produced by:** COR-008; some conventions were already implied by the github-issues bundle templates.

**COR-010 — Lifecycle of installed resources** · 2026-05-07
- **Motivation:** The core layer installs more than files (config files, symlinks, tracker labels, boards); nothing unified what "installed by core" means, how the methodology versions itself, or how component versions relate to it.
- **Key thinking / rejected alternatives:** Two version tiers (backbone + components with `requires_backbone` ranges), semantic versioning (package-manager precedent), a small backbone manifest + per-component manifests, migrations that write the manifest only when it is the source of truth, three migration scopes per tier, up-front compatibility resolution. Rejected: single global version; fully-independent versions; a single combined manifest; exhaustively listing derivable resources.
- **Builds on / produced by:** COR-001/002/004/005; the migration framework it introduces becomes rules/core.md #7 (mandatory migrations on surface changes).

### Structure matures — areas, agents, capabilities, schemas (COR-011..020)

**COR-011 — Areas as a first-class organizing concept** · 2026-05-07
- **Motivation:** Top-level `.pkit/` directories existed only as a convention; nothing named the *area* as a unit, fixed its contract, or governed adding new ones — and authoring tooling needs a dispatch target.
- **Key thinking / rejected alternatives:** Each area declares its own layout variant in its README (universal / adapter-umbrella / specialized); adopters can add areas (extension is first-class throughout); a scaffold command, not a doc. Rejected: implicit areas; one uniform layout; a closed area taxonomy; core-only areas; a parallel `.pkit/project/<area>/` tree.
- **Builds on / produced by:** COR-003 (two-namespace), COR-005 (adapter variant), COR-007 (scaffold-as-tooling).

**COR-012 — Scratchpad notes for exploratory drafts** · 2026-05-12
- **Motivation:** Large architectural questions need exploration before a record can be written; the only prior instance (`INVENTORY.md`) was an unformalised one-off with no lifecycle or relation to what it fed.
- **Key thinking / rejected alternatives:** A fifth content shape (not a sub-kind of doc); the folder *is* the state (single source of truth; retirement is a visible `git mv`); specialized area with flat layout; H1-in-body + date-in-filename; ship the stamp/move commands with the convention (recurrence is structural). Rejected: scratchpad-as-doc; universal variant (empty `core/`); status-in-frontmatter; no retired/abandoned distinction.
- **Builds on / produced by:** COR-006 (five shapes), COR-011 (specialized variant), COR-007; this record itself is what governs this very file.

**COR-013 — Agent architecture** · 2026-05-14
- **Motivation:** COR-006 named agents as a shape but not their internal structure — how references are declared, how operations execute across sources, how adopter-specific paths are reached, and how the agent matrix stays consistent.
- **Key thinking / rejected alternatives:** First-class agents area; unified frontmatter shape spanning agents + skills; references in frontmatter not prose (rename is YAML-aware); hooks (two-/three-segment names) instead of bundle-embedded or universal-contract agents; `project > bundle > adapter > core` precedence; placeholders + deploy-time overlay resolution; single overlay file with per-agent overrides; whole-category replacement. Rejected: per-bundle agent files; prose-only references; a hand-maintained matrix; per-agent overlay files; an abstract bundle contract upfront.
- **Builds on / produced by:** COR-006, COR-001 (mechanisms), COR-007 (contract emerges on recurrence).

**COR-014 — Universal applicability as the core/project split test** · 2026-05-14
- **Motivation:** CONTRIBUTING.md's COR-vs-PRJ test governed records, but the same question governs rules/skills/agents/hooks implicitly and had drifted — an audit found project-specific, bundle-specific, and harness-specific content shipped in `core`.
- **Key thinking / rejected alternatives:** Generalise the test to one cross-artifact principle ("does this fit an arbitrary adopter's tree?"), kept as a judgement question not a Boolean; the project namespace is symmetric across adopters (the framework self-hosts with no privilege); record it as a citable core record. Rejected: status quo implicit test; per-artifact-kind tests; records-only scope; a Boolean rule.
- **Builds on / produced by:** Generalises CONTRIBUTING.md; motivated by a rules/core.md audit; drives the rules/core.md vs rules/project.md split.

**COR-015 — Flat file vs folder layout for atomic vs composite artifacts** · 2026-05-15
- **Motivation:** Skills and agents shipped as per-name directories, but every skill to date was a single file — the folder wrapper was overhead without payoff, while folders are genuinely useful for helper-bearing artifacts.
- **Key thinking / rejected alternatives:** Conditional rule — flat when atomic, folder when composite — symmetric across skills and agents; drop the fixed `SKILL.md` name (adapter still produces the harness symlink); migrate the six atomic skills now while the count is small. Rejected: always-folders; always-flat; asymmetric per-kind rules; keeping `SKILL.md`.
- **Builds on / produced by:** COR-013 (agents area convention); extended by COR-020 for skill families.

**COR-016 — Design scripted scenarios via storyboard** · 2026-05-17
- **Motivation:** Many places run a scripted interaction with a human (review agent, CLI flow, migration wizard, tutorial); without a convention each author reinvents the format and design ambiguities surface late at implementation time.
- **Key thinking / rejected alternatives:** Name the principle broadly (Trigger / Preconditions / Walkthrough / Behind-the-scenes) but scope tooling narrowly to its first grounded class — agent-driven scenarios (COR-007 recurrence discipline); bind storyboards to *scenarios*, not to the implementing artifact's identity (an actor may run zero or more scripted scenarios).
- **Builds on / produced by:** COR-007, COR-013 (agents as first actor class).

**COR-017 — Capability pattern: opt-in installable disciplines** · 2026-05-18
- **Motivation:** Areas, bundles, and adapters existed, but nothing packaged a *discipline-level opt-in* (evidence citation, product-management, observability) — forcing every adopter to inherit it (violates COR-014) or scattering it into adopter namespaces.
- **Key thinking / rejected alternatives:** A new top-level sibling concept (not a fourth area variant — areas are mandatory); self-contained subtrees so ownership is structural (uninstall is `rm -rf`); directory-name citation namespace (`[evidence:DEC-001-slug]`) not 3-letter prefixes; install-time collision detection with interactive per-artifact resolution; uninstall refuses on dangling references rather than editing adopter prose. Rejected: capability-as-area-variant; projection into existing areas; prefix registries; refuse-all-on-collision; auto-uninstall; auto-strip references.
- **Builds on / produced by:** COR-011, COR-005, COR-014; grounded in an example-adopter evidence-management scratchpad + mis-classified core agents.

**COR-018 — Capabilities adopt the schemas mechanism as their engine-data layer** · 2026-05-20
- **Motivation:** A capability's quantitative/structural content (regexes, state names, field lists) must be consumed by code; hardcoding it in engine prose or parsing it from decisions both drift and are brittle.
- **Key thinking / rejected alternatives:** Capabilities adopt the schemas mechanism (YAML data + JSON Schema companions) — the linter/`.eslintrc` precedent; consumption via path-reference + transitive reachability (agent → skill → schema), reusing COR-013's reference graph. Rejected: hardcoding; runtime prose parsing; schemas declaring consumers; no declarative tracking; schemas inline in decisions.
- **Builds on / produced by:** COR-017 (named `schemas/` subdir), COR-013 (reference model).

**COR-019 — Cross-schema references use namespace-bearing tokens** · 2026-05-21
- **Motivation:** Two cross-schema reference forms were both sanctioned (bare id + field-name convention vs. `[namespace:id]`); practice showed bare ids break down in aggregator/multi-target cases.
- **Key thinking / rejected alternatives:** Settle on namespace-bearing tokens `[<namespace>:<id>]` (explicit target, survives aggregators, greppable); intra-schema references stay bare (no ambiguity within one file); settle now to keep one resolver/pattern. Rejected: bare-ids-permissive; allow both; `namespace/id` or `namespace::id` shapes; absolute file paths.
- **Builds on / produced by:** COR-018 (schemas mechanism).

**COR-020 — Skill families ship as one composite skill with sub-procedure files** · 2026-05-21
- **Motivation:** Families of related skill-operations (e.g. schema author/extend/rename/distill) shared a domain but shipped as N flat skills, growing the skills list linearly; COR-015 didn't settle the family case.
- **Key thinking / rejected alternatives:** One composite skill per family, canonical `<name>/<name>.md` dispatching to per-operation sub-procedure files (discoverability scales with families, not operations); reuse the canonical file as dispatcher (no `index.md`/`router.md`); fits inside COR-015 as a sub-case. Rejected: flat-per-operation; N composite skills per family; a faux umbrella skill; per-author choice.
- **Builds on / produced by:** COR-015 (composite-folder pattern); anchors the composite-skill regime (schema, pm, process, evidence, demo-recording skills).

### Capability ecosystem hardens — dispatch, data binding, review roles, ADRs (COR-021..030)

**COR-021 — Capability-command dispatch** · 2026-05-24
- **Motivation:** Capability scripts were invoked by raw filesystem path — undiscoverable, absent from `--help`, producing "file not found" on typos, and path-varying across adopters.
- **Key thinking / rejected alternatives:** Capabilities declare commands explicitly in `package.yaml`; the CLI registers them as a nested verb-subject tree; kit-shipped declaration is the only source (shared vocabulary across adopters); stateless registration at invocation time; direct-path invocation stays for backwards compatibility. Rejected: implicit filesystem scan; flat kebab tokens; per-adopter overrides; cached registration; per-capability top-level trees; a generic `pkit run`; deferring to a third consumer.
- **Builds on / produced by:** COR-017 (capabilities), COR-007 (two consumers = threshold); evidence + project-management drove it.

**COR-022 — Adopter data files bind to schemas via `pkit_schema:` with capability-declared fallbacks** · 2026-05-25
- **Motivation:** Adopter data files structurally follow a capability schema but nothing *says* so, breaking discovery, editor integration, and validate-against-schema.
- **Key thinking / rejected alternatives:** Field-first `pkit_schema:` binding with a capability-declared fallback; bare `<capability>:<schema>` reference (not bracketed); `pkit_` prefix avoids `$schema`/`schema:` collisions; refuse-on-version-mismatch (no auto-migrate); accept two sources of truth (field + IDE directive); a separate `pkit data validate` command.
- **Builds on / produced by:** COR-018/COR-019 (schemas + reference form); **superseded 13 days later by COR-023** on where the fallback lives.

**COR-023 — Bindings move inline via a `binds_to:` field on each schema** · 2026-05-25
- **Motivation:** COR-022's fallback lived in a separate `schemas/bindings.yaml` registry — an unnecessary layer forcing edits to two files and duplicating what a schema already knows about its data.
- **Key thinking / rejected alternatives:** Move the fallback inline as `binds_to:` on each schema YAML (one source of truth per schema, dies with the schema); everything else from COR-022 unchanged. Rejected: the `bindings.yaml` registry; per-file sidecar files; filename-only convention; IDE directive as canonical; pure capability-declared bindings.
- **Builds on / produced by:** Supersedes COR-022; refined at first-implementation review.

**COR-024 — Critic and architect agents** · 2026-05-27
- **Motivation:** AI-mediated authoring lets cheap-to-fix mistakes reach the human's expensive review loop, and lets locally-sensible changes drift architecturally — gaps the existing methodology/convention reviewers don't cover (no artifact/diff yet; architectural fit is broader).
- **Key thinking / rejected alternatives:** Two universal roles — `critic` (adversarial pre-proposal second opinion) and `architect` (architectural custodian, ADR custody); advisory-not-gate at v1 (COR-007 lets recurrence promote to gate); overlay-resolved doc roots. Rejected: one super-reviewer; architect-as-gate at v1; critic-as-hook; architect kit-internal only.
- **Builds on / produced by:** COR-006 (role decomposition), COR-007, COR-013 (overlay); coupled with COR-025 (ADR space).

**COR-025 — ADR decision space as a third namespace alongside COR and PRJ** · 2026-05-27
- **Motivation:** Adopters accumulate *architectural* decisions that don't fit PRJ (a how-we-work home); they land informally (comments, PRs, tribal knowledge) and mix into the PRJ corpus, hiding architecture among workflow conventions.
- **Key thinking / rejected alternatives:** Adopt Nygard-style ADRs as a third space under the adopter's `docs/architecture/decisions/` (not `.pkit/`, because ADRs are project- not kit-aware); four-section schema for uniformity with COR/PRJ/DEC; the `architect` agent is custodian. Rejected: PRJ-for-everything; architecture as a PRJ `kind` field; Nygard's three-section schema; ADRs under `.pkit/`; numbering shared with PRJ; no custodian; adopter-discretion-only.
- **Builds on / produced by:** Coupled with COR-024 (architect agent); PRJ-005 is project-kit's own adoption of it.

**COR-026 — Discipline-implying agents live in the capability that ships the discipline** · 2026-05-27
- **Motivation:** The placement rule for agents was never explicit; the "ship at core unless a capability home exists" default put discipline-implying agents (issues, evidence, storyboards) at core, forcing disciplines on adopters who lack the capability.
- **Key thinking / rejected alternatives:** An agent whose body implies a discipline lives inside that capability's boundary; grounded in COR-014 (universal applicability), COR-017 (opt-in), COR-006 (role bound to discipline), composition over decomposition. Rejected: no rule / author's judgment; inverse rule (promote execution agents to core); thin-core-shell + capability implementation.
- **Builds on / produced by:** COR-013, COR-014, COR-017; delivers COR-017's flagged retroactive reclassification.

**COR-027 — Alternative implementations live as capability-internal data, not as bundles** · 2026-05-27
- **Motivation:** COR-005's bundle pattern produced exactly one instance (`github-issues`) whose anticipated primitives were never built, the pm capability bypassed it, and every modular unit since became a capability — the bundle layer was an empty abstraction.
- **Key thinking / rejected alternatives:** Retire bundles entirely; handle in-capability variation as YAML data under `schemas/<aspect>/` (COR-018 mechanism); lived evidence outranks initial design (COR-007); pre-1.0 tolerates the breaking CLI removal (PRJ-002). Rejected: keep COR-005 as-is; no-op stubs; migrate the bundle into pm; bundles as a capability sub-shape.
- **Builds on / produced by:** Supersedes COR-005's bundle half; grounded in project-management DEC-003/DEC-008.

**COR-028 — Permission model realized by adapters** · 2026-05-29
- **Motivation:** Adopters configure harness permissions directly in harness-native form — no domain-level view, no fault localization, and hand-editing low-level config; harnesses also differ in what they can enforce.
- **Key thinking / rejected alternatives:** One domain-term source of truth realized by each adapter to its harness (reuse of COR-013's neutral-content/adapter-translation split); honesty about un-enforceable intents (auditable gaps); additive/adopter-sovereign default with opt-in managed ownership. Rejected: configure harness-native directly; a single runtime interceptor as sole authority; a least-common-denominator model.
- **Builds on / produced by:** COR-013, COR-002 (merge delivery); realized by PRJ-006 (permission-prompt diagnostics) and rules 14/15; explored in the self-service-tool-update scratchpad line.

**COR-029 — Adopter-data references resolve through the binding to the bound instance** · 2026-06-11
- **Motivation:** Combining COR-019's typed-token references with COR-023's adopter-data binding produces cross-file references neither validates — a schema describing adopter data keeps its id collection empty by design, so a dangling reference passes silently.
- **Key thinking / rejected alternatives:** Refine COR-019 so the collection is located *by following the binding* to the bound instance (not the schema's own always-empty collection); the token form and capability-side behaviour are unchanged; non-reference bracketed tokens in prose must not be misread.
- **Builds on / produced by:** COR-019 (reference form), COR-023 (binding); explored in per-project-version-pin / audit-journal scratchpad lines around this era.

**COR-030 — Capabilities declare versioned dependencies on other capabilities** · 2026-06-17
- **Motivation:** Capabilities build on one another but could declare only `requires_backbone`; a dependency could be absent, or present-but-incompatibly-evolved (the insidious silent-at-runtime failure).
- **Key thinking / rejected alternatives:** A versioned dependency edge (not presence-only), reusing the backbone-compatibility resolver on a second axis; refuse-with-hint rather than auto-cascade; direction-split disposition (refuse when installing a dependent, warn-and-override when upgrading a dependency); the real guarantee is a runtime guard in the dependent. Rejected: presence-only; a full topological resolver with cascade; coupling the edge to permission contributions.
- **Builds on / produced by:** COR-017 (capabilities), COR-010 (compatibility resolution), COR-028 (permission contributions kept orthogonal).

### The process substrate era — a content-free state-machine engine, un-deferred slot by slot (COR-031..040)

**COR-031 — A capability has an origin: kit-shipped or incubated-in-repo** · 2026-06-20
- **Motivation:** COR-017's install/sync lifecycle assumed capabilities are copied from kit source; a capability an adopter *authors in its own repo* has no upstream, so sync misclassifies it as kit-content-gone-missing and can overwrite adopter work.
- **Key thinking / rejected alternatives:** Model origin as a one-bit property (not two lifecycles); sync *skips* incubated capabilities (correct no-shared-files semantics, not a degraded warning); default absent origin to `kit-shipped` (additive, migration-free); defer external-source + graduation until a consumer exists. Rejected: a separate "local capability" concept; treat-as-kit-shipped-and-warn; require a migration; derive origin from kit-source presence; specify external sources now.
- **Builds on / produced by:** COR-017, COR-001 (no-shared-files), COR-010 (additivity), COR-007.

**COR-032 — A process may track many keyed subjects under one definition** · 2026-06-21
- **Motivation:** COR-033's substrate shipped `singleton`-only and named `keyed` as a deferred slot; the issue lifecycle (many issues, each at its own position) is the binding that demands it.
- **Key thinking / rejected alternatives:** Ship `keyed` minimally — "operate per the supplied subject" plus a cardinality value and descriptive key; the engine already journals per-subject so it is threading an identifier, not new mechanism; exclude enumeration and cross-subject cascade (that is breadth). Rejected: shipping enumeration/cascade with `keyed`; modelling each subject as its own singleton.
- **Builds on / produced by:** COR-033 (P5 slot), COR-007 (recurrence); draws the line COR-037 later crosses deliberately.

**COR-033 — Capabilities bind process definitions to a shared, content-free process substrate** · 2026-06-21
- **Motivation:** Several disciplines run staged, gated state machines (issue lifecycle, design-maturity, trip pipeline); re-hand-rolling a bespoke engine per discipline duplicates the hardest part (the guarded state machine) and lets copies drift.
- **Key thinking / rejected alternatives:** Backbone owns the *shape*, capability owns the *instance*; position is inferred-from-reality (P3); gates are checkable and cross-authority (an actor can't talk its way past — the load-bearing guarantee, P4); name-broad/ship-narrow (P5/P6) — name the variation axes, ship only the grounded core, un-defer per binding. Rejected: generalise one capability's schema in place; a central content-bearing schema; leave each discipline to hand-roll.
- **Builds on / produced by:** COR-007, COR-023 (binding grammar untouched); the foundation the whole COR-032/034/035/036/037/038/040 sequence un-defers.

**COR-034 — A blocked subject is a first-class, self-clearing wait, not a definition state** · 2026-06-22
- **Motivation:** The bare "no legal move" detection can't express *what* a subject waits on, *since when*, and *on whom*; two bindings need more — pm's parked-in-review issues, and trip-planning's human-decision pauses vs. awaiting-the-world pauses that resume by themselves.
- **Key thinking / rejected alternatives:** Ship a first-class `blocked{blocked_on, resume_when}` record minimally; two bindings meet the P5 gate; keep it a self-clearing wait, not a definition state.
- **Builds on / produced by:** COR-033 (P5 slot, derived-blocked detection), COR-007, COR-016 (name-broad/ship-narrow).

**COR-035 — A process may declare invariants: position-independent always-checks** · 2026-06-22
- **Motivation:** Detection and gates answer "where am I?" / "may I move?" but not rules that must hold at *every* position — pm's structural rules; trip-planning's evidence-backed facts, scope-containment, derive-don't-store.
- **Key thinking / rejected alternatives:** Ship the slot minimally — a `{id, check, why}` declaration + a new engine `validate` operation reusing the existing predicate runner; process-wide only (not per-state) and report-only (not move-blocking) — both the deliberately minimal cut, deferring `applies_to` scoping and enforcement to the open-region slot that needs them. Rejected: couple invariants to move-blocking now; per-state scoping now; severity/auto-remediation; capability-local always-checks; cross-subject invariants.
- **Builds on / produced by:** COR-033, COR-032 (single-subject line), COR-016; its deferrals are fulfilled additively by COR-040.

**COR-036 — A process resolves another's terminal outcome; composition is that resolution, embedded** · 2026-06-22
- **Motivation:** Composition — one process embedded in another, the inner outcome feeding the outer's gate — needs genuinely new machinery: cross-process outcome resolution; grounded in trip-planning's per-point verification mini-process embedded in area-discovery.
- **Key thinking / rejected alternatives:** Design the cross-process resolution *once* as its own capability with two consumers (composition here, cascade later); fold composition in (bare resolution has nothing to invoke it); resolve *one* determinate inner, never an aggregate (the cascade boundary); forbid cycles (first place a cycle is expressible). Rejected: a third "bare resolution" record; folding the aggregate in here.
- **Builds on / produced by:** COR-033 (P5, P3 position guarantee), COR-032 (enumeration line), COR-007; the foundational unit COR-037 consumes.

**COR-037 — A parent process may fold one child process's subject outcomes into a gate** · 2026-06-23
- **Motivation:** The last P5 breadth slot — reading across a keyed child's subjects and folding into a parent gate; two independent bindings demand it (pm closure cascade: parent closes when every child is done; trip-planning: area closes when every point reaches `verified`).
- **Key thinking / rejected alternatives:** Un-defer minimally — `all` + `count` (one enumerate-and-fold machine, two reducers), child→parent, one declared relation, fail-closed; the first deliberate crossing of COR-032's no-enumeration line, *necessary* because gates are engine-evaluated; reuses COR-036's single-inner resolution as the per-subject step; breadth not depth (engine stays single-level, P3/P6 intact). Rejected: keep cascade capability-local forever; capability folds its own subjects (a fold the engine can't read can't gate); a general enumeration API; richer reducers now; the other cross-subject machines now.
- **Builds on / produced by:** COR-036 (resolution), COR-032 (the line it crosses), COR-033 P5, COR-007.

**COR-038 — A process declares cross-process connections as inert visible metadata; the engine stays pull-only** · 2026-06-26
- **Motivation:** As capabilities compose, the workflow topology is the load-bearing fact but only partly visible — `subprocess`/`cascade` edges are engine-visible, while gate-predicate dependencies and advisory couplings are buried or tribal; and whether the substrate is ever event-driven was undecided.
- **Key thinking / rejected alternatives:** A `depends_on` annotation that is inert-but-schema'd (visibility without re-introducing unenforceable enforcement); derive-don't-annotate for edges that already have enforcing declarations (single source of truth, COR-006); the engine stays *pull-only* (live detection, P3) — reaction/push is a different job at the deferred orchestration altitude. Rejected: an enforcing `upstream-gate` engine kind (illusory first-classness, reads flapping peer positions); a project-level process-graph manifest (second wiring mechanism); a uniform annotation over every connection; a push/event channel.
- **Builds on / produced by:** COR-033 (P3 live detection), COR-036/COR-037 (the visible edges), COR-035 (report-only precedent), COR-006.

**COR-039 — A session mutates its own repo's context; cross-repo mutation is operator-gated, never silent** · 2026-06-30
- **Motivation:** A session rooted in repo A can reach into repo B (cd or path-redirect) and mutate B under A's governance — B's rules/conventions/agents/permission model never load. It happened concretely (issues filed, decisions authored, commits landed in a separate adopter repo).
- **Key thinking / rejected alternatives:** Operator-gated exception, not a blanket block (cross-repo coordination is legitimate; per-change human gate); the honest lever is an interlock at the mutating program (the only layer that knows both session root and target); honest-about-reach, not a claimed wall (an interlock against accidental handoff + a discipline rule, residual gap declared per COR-028's honesty discipline). Rejected: block outright; enforce in the intent layer (defeated by cd/redirect); rely on filesystem confinement (partial where tools run unconfined); a discipline rule alone.
- **Builds on / produced by:** COR-028 (honesty discipline), COR-024 (advisory posture); realized as rules/core.md #18.

**COR-040 — A process may declare an open region: a free-order state bounded by invariants and an exit gate** · 2026-07-01
- **Motivation:** COR-033 named an *open region* (a state bounded only by invariants + an exit gate) as the escape hatch for open-ended work; trip-planning's `build` phase — discovery/route/logistics/safety accumulating in no fixed order and looping — demands it.
- **Key thinking / rejected alternatives:** Ship one state whose internal progress is data accumulation and whose only structured move is its exit (not a sub-state container — that reintroduces ordering; staged items use COR-036 composition); the exit is a *gate*, not a special invariant (keeps the always-true/may-move line); boundary-enforcement via gate-predicate composition, not move-blocking invariants (fulfils COR-035's deferral additively); mutation enforcement stays with the binding; liveness out of scope. Rejected: sub-state-and-edge sublanguage; exit-as-invariant; engine-intercepts-every-write.
- **Builds on / produced by:** COR-033 (P5/P6 open-region slot), COR-035 (un-defers its per-state + enforcing posture together), COR-036, COR-007.

### Distribution, health, and authoring maturity (COR-041..044)

**COR-041 — Externally-sourced content is pulled whole, pinned, and reconciled against its source** · 2026-07-06
- **Motivation:** COR-031 reserved the `externally-sourced` origin and deferred its mechanism; the grounded consumer arrived — an org privately sharing adopter-owned content (a proprietary capability, or a company house-style) across its own repos without publishing upstream or forking.
- **Key thinking / rejected alternatives:** Consumed-whole + match-the-pin is the only reconcile shape consistent with the no-shared-files invariant (merging shared content into an owned region is the exact conflict machinery the methodology refuses — use suspension/precedence instead); ship a house-style as a capability consumed whole (no new artifact type); registry-free pin-by-ref minimalism; the project-specific fetch/auth write-path is delegated to a realising ADR.
- **Builds on / produced by:** COR-031 (reserved origin), COR-001 (no-shared-files), COR-006, COR-007, COR-025 (ADR delegation).

**COR-042 — A connection may declare an evaluable hand-off contract; a report-only health check detects missed hand-offs** · 2026-08-07
- **Motivation:** COR-038's `depends_on` topology is drawable but not evaluated; an adopter running a design process coupled to delivery hit a live gap — every upstream subject had reached the hand-off state and downstream had picked up none, with nothing able to say so. The request: detection before remediation.
- **Key thinking / rejected alternatives:** A new report-only `health` operation that reads across two connected processes' crowds and reports gaps; opt-in evaluable `constrained-with` (not evaluating every coupling — that would retroactively burden inert COR-038 annotations); existence not downstream-position (ship-narrow); the read is safe *because* nothing rides on it (report-only, snapshot semantics), unlike COR-038's rejected enforcing gate; substrate-shipped for a shared surface (not capability-local); narrowly re-scopes COR-038's "never evaluated" ruling rather than leaving two records in tension. Rejected: extend `validate`; surface on `status` (taxes the hot path); an enforcing posture; implicit evaluation; capability-local; a stored reverse index as *the* mechanism (drifts / lies).
- **Builds on / produced by:** COR-038 (re-scoped), COR-035 (deferred cross-subject slot, shared-surface precedent), COR-037, COR-007, COR-025.

**COR-043 — A scratchpad note may enter an optional reported side-state when sent through the report channel** · 2026-08-10
- **Motivation:** COR-012 notes and the universal report surface meet in practice (the richest problem descriptions *are* notes sent upstream); once sent, nothing records where it went, how it's doing, or whether the local file has drifted from the as-sent text.
- **Key thinking / rejected alternatives:** A core `reported` *side-state* (binds to the universal report surface, meaningful in every project), not a fourth stage (would force every brainstorming note through a "was this reported?" question and muddy the pure brainstorming role); freeze-plus-hash-detect rather than a write gate (a hard gate on files anything edits is theatre); live pull-only read-back of upstream status (a stored status is a second copy that lies — the COR-038 argument). Rejected: a general `tracked` state; a fourth lifecycle stage.
- **Builds on / produced by:** COR-012 (three-state lifecycle, folder-as-state), COR-038 (don't-store-what-you-can-read), the report CLI surface (PRJ-008).

**COR-044 — Process authoring ships as a core layer: composite skill for the shape, owner-scoped agent for the teeth** · 2026-08-11
- **Motivation:** The process substrate is complete enough to author against, but there is no authoring layer — a definition owner must know the substrate records by heart and hand-edit. The load-bearing observation: a definition has two halves of different kinds — the declarative *shape* (closed vocabulary) and the domain-logic *teeth* (detection/gate predicates).
- **Key thinking / rejected alternatives:** Two carriers — a composite `process` skill for the shape, an owner-scoped `process-author` agent for the teeth (COR-006 carrier discrimination: procedure vs. judgment); owner-scoped makes the agent safe to ship at core (same authority the owner already has by hand); straight to core, not a capability (the substrate ships with the backbone — an authoring layer whose subject every adopter has fails the opt-in test); a closed op set read as data (absorbs vocabulary growth without skill edits); substrate-altitude substitution test (nothing may assume a development domain). Rejected: one skill no agent (leaves the teeth to hand-authoring); a teeth *skill* (reintroduces an optional-producer dependency); fold into an existing producer agent; a `process-authoring` capability; a cross-owner composer; an open-ended op set.
- **Builds on / produced by:** COR-033 + the whole process sequence, COR-020 (composite-skill precedent, schema-authoring), COR-026 (agent placement), COR-006, COR-017; ships the `process` skill + `process-author` agent.

### Project-side decisions (PRJ-001..009)

_project-kit self-hosts, so these are the framework's own PRJ records — the non-universal choices that fail COR-014's universal-applicability test and stay in the project namespace._

**PRJ-001 — CLI binary name is `pkit`** · 2026-05-06
- **Motivation:** COR-004 deferred the CLI binary name to the implementing project; project-kit is that project.
- **Key thinking / rejected alternatives:** `pkit` — short, mnemonic, lowercase, no notable collisions. Rejected: `pk` (collides with FreeBSD's package manager); `kit` (too generic/ambiguous); `projk`/`prkit` (no advantage); `project-kit` (too long, awkward hyphens).
- **Builds on / produced by:** COR-004.

**PRJ-002 — Version-bump policy (declared, release-driven)** · 2026-05-08
- **Motivation:** COR-010 fixed semver + tiers but deliberately left *when* and *who* bumps to the project; per-PR-with-no-rule risks version churn or version freeze, both destroying the compatibility signal.
- **Key thinking / rejected alternatives:** Promoted from a pre-1.0 hybrid to *declared per-PR, applied release-driven, written main-only* — surface changes drop a `changie` changeset naming `component → segment`; the segment is a human surface judgment (a 20-commit analysis showed CC type predicts neither segment nor tier); numbers are written only on `main` by a release step (removes the merge-conflict-on-version-cells class seen on PR #360); `requires_backbone` broadening moves to the release step; decision-touching PRs declare by self-executing vs design-ahead. Rejected: bump-in-surface-PR (the retired hybrid); bump every merged PR; calver; a blanket `.pkit/decisions/` guard exemption.
- **Builds on / produced by:** COR-010, COR-007 (release tooling), COR-008/009 (conventions as surface); realized as rules and the release-flow spec; extended by PRJ-007.

**PRJ-003 — Implementation language for the runtime is Python** · 2026-05-08
- **Motivation:** The bash dispatcher bootstraps `init`/`status`/etc. but cannot carry COR-004's full surface — manifest schemas, version resolution, argparse, validation, migration orchestration all need structured-data handling past bash.
- **Key thinking / rejected alternatives:** Python 3.11+, `pyproject.toml`/PEP 621, minimal deps (`ruamel.yaml`, `click`/`typer`, `packaging`), distributed via `uv tool install`; chosen for structured-data velocity, adopter-ecosystem cohesion (near-term adopters are Python), acceptable startup cost. Rejected: Go/Rust (single-binary wins don't pay for authoring-velocity loss, lossier YAML round-trip); TS/Node (ecosystem churn, adopters not all Node); stay-shell; multi-language; bare `uv run` scripts.
- **Builds on / produced by:** COR-004, COR-010; grandfathered as PRJ (not ADR) by PRJ-005.

**PRJ-004 — Distribution via direct git URL on github.com (no registry)** · 2026-05-08
- **Motivation:** PRJ-003 settled the language and `uv` frontend; *where* to install from remained — registry vs. direct-from-source.
- **Key thinking / rejected alternatives:** Install directly from the public git URL, no registry layer; `uv tool install git+ssh://...` is the sole sanctioned frontend (the `pip install` fallback was dropped because the router hard-assumes `uvx` for pinned re-execution and self-update instructs `uv`); registry-free minimalism fits a small manually-growing adopter set. Rejected: PyPI/private registry/Homebrew/tarball/`curl|bash`; keeping the `pip` fallback.
- **Builds on / produced by:** PRJ-003; mandates annotated tags reused by PRJ-002's release step; realized in ADR-039/ADR-044.

**PRJ-005 — Adopt ADRs for project-kit's architectural decisions** · 2026-05-27
- **Motivation:** COR-025 made ADRs an opt-in adopter affordance and explicitly commissioned a PRJ record on whether project-kit's own architecture warrants them.
- **Key thinking / rejected alternatives:** Adopt the ADR namespace at `docs/architecture/decisions/`; a classifier table leans PRJ for kit-internal mechanism choices, ADR when rationale must be findable by a future maintainer orienting in the codebase; no retroactive backfill (PRJ-003 stays PRJ, per COR-025's stance); self-hosting validates the affordance in its source repo. Rejected: defer until a decision demands it; reclassify PRJ-003; a `kind:` field on PRJs; amend COR-025 to cap PRJ scope.
- **Builds on / produced by:** COR-025 (delegated the question), COR-024 (gives the architect agent a corpus), COR-014.

**PRJ-006 — Opt-in permission-prompt diagnostic loop** · 2026-06-19
- **Motivation:** Under autonomy, confirmation prompts recur with no systematic way to see which recur, why, or what would stop them — prompt-reduction was only half a feedback loop (remediation happened ad hoc; the capture→classify→measure spine didn't exist).
- **Key thinking / rejected alternatives:** `pkit permissions diagnose on|off|status|report` — opt-in, off by default (per-call cost/privacy); capture in the adapter not the pure decision core; advisory classification gated by a curated safe-set; an auto-fix bright line resolved on paper (may auto-grant an existing catalog privilege, never mint a new one — intent erosion, not a security breach per ADR-004); defer the generic diagnostics framework until a second probe recurs (COR-007). Rejected: always-on; capture in core; classifier-as-gate.
- **Builds on / produced by:** COR-028 + its ADRs (permission model observed, not changed), COR-007; sibling to the version-bump policy as project tooling; grounded in a scratchpad note.

**PRJ-007 — The release step keeps the self-host backbone manifest current** · 2026-07-10
- **Motivation:** The source repo self-hosts but never runs install/sync on itself, so its manifest `backbone_version` froze at genesis (`1.0.0`) while `.pkit/VERSION` advanced — making `pkit status` permanently misreport the self-host backbone as far behind.
- **Key thinking / rejected alternatives:** `pkit release apply` writes the self-host `backbone_version` whenever it bumps the backbone (durable root-cause fix; the release is the exact moment the source backbone changes); self-host-only mechanics, adopters unchanged; a one-time reconciliation lands with it; the two-writer arrangement is named as a deliberate self-hosting consequence. Rejected: leave-as-is (permanent misreport, dead field); one-time correction only (re-rots); special-case `pkit status` display.
- **Builds on / produced by:** PRJ-002 (extends what `release apply` writes), COR-010 (manifest), COR-014.

**PRJ-008 — `pkit report` — a built-in adopter→project-kit feedback channel** · 2026-08-07
- **Motivation:** An adopter (Mike, pkit 1.105) hit friction with no first-class way to report it — hand-filed issues lack version/environment context and have no progress read-back; for a solo-maintained tool the tracking half is the adoption flywheel.
- **Key thinking / rejected alternatives:** Ship a `pkit report` family — universal reporter side (bug/feedback/change-request + read-back), target-repo-gated maintainer side (inbox/link); the *target* is distribution-level project config (not a neutral-core constant, not a `--repo` flag — keeps the backbone free of a hard-wired phone-home, COR-014); tracking via a `## Tracked by` task-list (many-to-many, chosen over native single-parent sub-issues); on-behalf = attribution not authorship; the reporter side is the first realization of COR-039's cross-repo exception (target-naming confirm, URL-first, degrade-to-draft under `--yes`, redaction by construction). Later refinement added `change-request` as a sibling verb. Rejected: conflating with pm's maintainer→spec channel; native sub-issues; a `derived-from:` label; a `--kind` flag for CR.
- **Builds on / produced by:** COR-039 (cross-repo boundary), COR-014, COR-007; realized in ADR-047; feeds COR-043 (reported scratchpad side-state).

**PRJ-009 — project-kit dogfoods its own code-review panel** · 2026-08-24
- **Motivation:** The `software-engineering` capability's code-review panel shipped (v1.149.0) to close report #715 (a merge gate could read APPROVED with zero code reviewed), but wasn't registered in project-kit's own manifest — so #715's exact gap stayed live on the repo that authored the fix.
- **Key thinking / rejected alternatives:** Register the in-repo capability via `pkit capabilities register` (COR-031 in-place register, origin `incubated-in-repo`) — not `install` (which copies from kit source); satisfy the COR-030 pm `>=0.54.0` dependency and reconcile pm's stale installed record; no new content, pure project-side config turning on released functionality. Dogfooding is the honesty position and the tightest reviewer-tuning loop.
- **Builds on / produced by:** COR-031 (in-repo register), COR-030 (capability dependency), software-engineering + project-management capability DECs; COR-014 (install-state is project-side).

### Exploratory notes that fed decisions (retired scratchpads in `done/`)

_Per COR-012, large architectural questions are mapped in a scratchpad note before a record can be written; these are the retired ones, with the pre-decision thinking they captured and what each `produced`. Many produced capability DECs / ADRs (outside the COR/PRJ corpus above), which is where the process-substrate and pm work actually landed._

- **2026-06-21 — Process primitive** · started 2026-06-21, retired 2026-06-22 · produced **COR-033, COR-032**
  - Explored the shape of a reusable mechanism for *staged, guided, gated* processes that grow incrementally — designed as an abstract core but grounded against real instances, not speculatively (owns EPIC #127, "generalise the workflow state machine"). This is the pre-decision map behind the entire process-substrate era: it directly produced the substrate (COR-033) and the keyed-subjects slot (COR-032).

- **2026-06-23 — Multi-clone issue ownership** · started/retired 2026-06-23 · produced **DEC-035** (project-management capability)
  - Explored how one person running several clones of the same repo (each with its own `project-manager` session) can distinguish, claim, and respect each other's in-flight work when GitHub shows the same human as assignee everywhere — without forcing that complexity on the common single-clone case. Fed a pm-capability DEC, not a COR.

- **2026-06-23 — project-management on brownfield repos** · started 2026-06-23, retired 2026-06-24 · produced **DEC-036** (project-management)
  - Explored how the pm capability adapts to an existing *immutable* substrate — remapping its conceptual needs (type/priority/workstream/state labels, boards) onto what a brownfield repo already has, degrading gracefully, tolerating unmanaged attributes — so a brownfield adopter keeps as much methodology as the substrate allows instead of being blocked wholesale (grounding case: AUJ, where labels can't be created at all). Greenfield stays easy; brownfield becomes a supported mode.

- **2026-06-24 — Brownfield adoption ceremonies** · started/retired 2026-06-24 · produced **DEC-037** (project-management)
  - Follow-on to the brownfield note: explored adopter-supplied *attribute population* at adoption (setting every issue's `workstream` to an adopter value like `Spyre`; assigning milestones) as a hook/script slot the adopter fills, run through an auditable ceremony, with presets harvested from real adopters — reusing existing pkit systems rather than inventing new ones.

- **2026-07-03 — Private company content distribution** · started 2026-07-03, retired 2026-07-07 · produced **COR-041, ADR-040**
  - Explored how a company privately shares adopter-owned pkit content across its own repos — spanning a whole private capability and a company overlay/profile on a kit-shipped capability — maintained in one place, consumed internally, without publishing upstream or forking. The pre-decision map behind COR-041 (externally-sourced distribution) plus its realising ADR.

- **2026-07-31 — Self-service tool update** · started 2026-07-31, retired 2026-08-03 · produced **ADR-044, PRJ-004, #574**
  - Explored whether/how pkit can fetch/run/repoint to the latest released tool on its own — the two-manual-step upgrade gap (`uv tool install --force` then `pkit upgrade`) where an adopter got "already at backbone vX" against a stale global tool. Fed PRJ-004's dropping of the `pip` fallback and the self-update detect-and-instruct ADR.

- **2026-08-05 — Per-project version pin (Option D)** · started 2026-08-05, retired 2026-08-06 · produced **ADR-049**
  - Explored making the ADR-039 router's per-project pin real for adopters — the router re-execs `uvx project-kit@<pin>` but `_resolve_pin` reads `.pkit/VERSION`, which adopters don't have, so every adopter runs the global binary with no version-locking. The payoff: `pkit upgrade` becomes an in-project pin-raise served ephemerally via `uvx`, no global tool mutation, avoiding the costs that sank ADR-044's auto-install path.

- **2026-08-11 — Audit journal model** · started 2026-08-11, retired 2026-08-12 · produced **DEC-049** (project-management)
  - Revisited the pm capability's audit/journal surface as a whole (prompted by #672's confusing double/missing comments) to define *why/when/how* an audit comment is used before fixing formats piecemeal. The load-bearing conclusion: GitHub's timeline is the state journal; an audit comment earns its keep only for *intent the substrate can't capture* — the justification for an override/authorisation — not a duplicate state log.

## Cross-cutting threads

Recurring ideas that appear across many CORs, independent of era:

- **Principles, not inventory.** A decision records the durable *rule*; the current list of paths/commands/states/labels lives in an area README or manifest that churns. Explicit in COR-003, COR-004, and reasserted whenever a record refuses to pin a list (COR-011, COR-012's labels-in-README, COR-035's vocabulary-as-data, COR-044's op-set-read-as-data).

- **Extract on recurrence, never on anticipation (COR-007).** The corpus's most-cited discipline. Two grounded consumers is the threshold to build (COR-017, COR-021); one binding un-defers a named single-subject slot (COR-032, COR-034); the same discipline retires an abstraction with no second consumer (COR-027 kills bundles). Applied recursively to the methodology itself.

- **Name-broad / ship-narrow (COR-016, COR-033 P5/P6).** Name the general principle or the full variation space, but ship tooling/mechanism only for the grounded case. The entire process-substrate sequence (COR-032/034/035/036/037/040/042) is this pattern executed slot by slot.

- **The no-shared-files invariant (COR-001).** One owner per file. Reappears as the reason merge exists (COR-002), as suspension's contractual line (COR-003), as capability self-contained subtrees (COR-017), as incubated-capability sync-skip (COR-031), and as consumed-whole external sources refusing merge machinery (COR-041). The session-level analogue is COR-039.

- **Honesty about what a mechanism cannot do.** Report the gap rather than hide it: permission-model un-enforceable intents (COR-028), the cross-repo interlock that is "an interlock against accidental handoff, not a security boundary" (COR-039), report-only invariants and health checks (COR-035, COR-042), and explicit supersession/re-scope when two records would otherwise silently disagree (COR-023, COR-042 re-scoping COR-038).

- **Derive / read-live, don't store.** A stored copy of truth that lives elsewhere will drift into a lie. Drives derive-don't-annotate (COR-038), the health check reading live positions (COR-042), scratchpad `reported` live read-back (COR-043), and the derive-don't-store invariant itself in trip-planning.

- **Carrier discrimination (COR-006).** Match content to its artifact shape — why over what-is over procedure over role over exploration. Decides skill-vs-agent splits (COR-044), skill-vs-command pairing (COR-005), scratchpad-as-fifth-shape (COR-012), and reviewer-role decomposition (COR-024).

- **Advisory / operator-gated over hard-blocking.** Prefer a per-change human gate or advisory posture to a wall: architect advisory-not-gate (COR-024), refuse-with-hint over auto-cascade (COR-030), operator-gated cross-repo exception (COR-039), recommend-don't-apply diagnostics (PRJ-006), degrade-to-draft reporting (PRJ-008).

- **Adopter sovereignty / project-namespace symmetry (COR-014).** Every adopter has a project side, including the self-hosting framework, with no privilege. Drives the additive defaults (COR-028, COR-031), the never-edit-adopter-prose disposition (COR-017 uninstall), and the whole PRJ corpus as project-kit's own non-universal rules.

- **Self-correction in the record stream.** The corpus visibly fixes itself: COR-023 supersedes COR-022 within the same day; COR-027 retires COR-005's bundles on lived evidence; COR-042 narrowly re-scopes an accepted foundational sentence in COR-038; PRJ-002 is promoted from its pre-1.0 hybrid. Supersession is treated as normal maintenance, not failure.



## Honesty / inferred flags

Where this timeline reports documented fact vs. where it inferred:

- **Motivations are well-documented throughout.** Every COR and PRJ carries an explicit `## Context` section stating the problem, and most carry `## Rationale` + `### Alternatives considered`. The per-entry "Motivation" and "Key thinking" bullets are paraphrases of that documented content, not reconstructions. Confidence is high across the whole corpus.

- **Dates are authored dates (frontmatter `date`), not commit dates.** Git history begins 2026-06-13 (the public import), so records dated May 2026 predate the visible git history — their dates come from frontmatter and are taken at face value. Not independently verified against any pre-import history.

- **"Builds on / produced by" links are a mix of stated and inferred.** Explicit `supersedes:`/citation links (COR-023→022, COR-027→005, COR-041→031, PRJ-005←025) are documented. Softer lineage claims — e.g. tying a COR to the scratchpad that "explored" it — are inferred from the scratchpad `produced:` frontmatter where present, and from thematic proximity where not. The scratchpad→COR links in Cluster G are all documented via `produced:` frontmatter; the reverse annotations added to some Cluster A–D entries (e.g. "explored in the audit-journal scratchpad line") are looser thematic inferences, marked with hedging language.

- **Cluster G notes produced capability DECs / ADRs, not CORs.** Four of the eight retired scratchpads produced project-management-capability DEC records or ADRs (DEC-035/036/037/049, ADR-040/044/049) that are outside the COR/PRJ corpus this timeline enumerates. Their `produced:` refs are reported verbatim from frontmatter; the content of those DEC/ADR records was not read for this timeline (out of the stated scope).

- **Section extraction was mechanical.** Entries were built from each record's `## Context`, `## Rationale`, and `### Alternatives considered` sections via scripted extraction; a few records embed template/example fragments (e.g. a "Japan (Tokyo)" schema sample in COR-022/023, a template stub in COR-025) that were recognised as examples and excluded — no motivation was drawn from them.

- **Not exhaustively cross-checked against implementation.** This is an archaeology of the *decision records*, not of the code. Where a record says a feature "ships" or was "realized in ADR-NNN", that is the record's own claim, not verified against the shipped CLI or capability trees.

