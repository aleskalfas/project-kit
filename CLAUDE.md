# Claude Code instructions — project-kit

This is project-kit's own source repo — the methodology framework itself, not an adopting project. project-kit self-hosts.

@.pkit/rules/core.md
@.pkit/rules/project.md

## Where to find what

- **`CONTRIBUTING.md`** — kit-maintainer guidance. **Read before authoring or amending any COR record.** Covers the math/physics framing, axiom discipline, project-neutrality, and the principles-not-inventory rule.
- **`.pkit/decisions/README.md`** — adopter-facing spec for the decision-record system (schema, statuses, namespaces, the no-shared-files invariant). **Read before working with any record.**
- **`.pkit/decisions/core/COR-NNN-*.md`** — accepted core records. Read in order; each builds on its predecessors.
- **`.pkit/scratchpad/README.md`** — area spec for scratchpad notes (exploratory working drafts that retire by producing records/docs or being abandoned). See COR-012 for the principles.
- **`.pkit/scratchpad/done/2026-05-04-inventory.md`** — kit-internal working note from the walk through `example-brownfield`. Source of many structural decisions (COR-001, COR-002, COR-003, COR-005 at minimum); not synced. First retired scratchpad note under the COR-012 convention.
- **`.pkit/cli/README.md`** — CLI command spec, with cross-references back to COR-004 for design rules.
- **`.pkit/agents/README.md`** — agents area spec. Four universal core agents shipped today: `critic` (adversarial pre-proposal review per COR-024), `architect` (architectural custodian + ADR custody per COR-024 + COR-025), `methodology-reviewer` (disciplines audit on artifacts), `convention-compliance-reviewer` (diff checks against conventions). Deployed by `.pkit/adapters/claude-code/deploy-agents.sh`. The project-management capability ships `project-manager` (file/validate/transition issues + autonomous batch-planning) per [COR-026](.pkit/decisions/core/COR-026-agent-placement-by-discipline.md) + [project-management:DEC-029-project-manager-agent-shape]; install the capability to use it.

## Session style

- **Minimal ceremony.** Trim structure that doesn't earn its keep at current scale. Default lean.
- **Terse output.** State results and decisions directly; no trailing summaries.
- **CORs avoid the word "kit"** — speak in core/project terms. Adopter-facing READMEs and `CONTRIBUTING.md` may use "kit" or "project-kit" freely.
- **Acceptance gate.** Only act on `accepted` decisions. Proposed records are draft hypotheses; authoring work that would cite one violates the gate. Accept first (one-line status flip + commit) or pause. See `.pkit/decisions/README.md` "The acceptance gate".
- **Pattern extraction (COR-007).** When the same shape of work recurs, invest in tooling — a skill, agent, decision, doc, script, or template — rather than repeating the manual work. Apply COR-006's discriminator to choose the carrier.
- **Exploratory work (COR-012).** Architectural questions too large for an immediate record live as scratchpad notes under `.pkit/scratchpad/`. Use `pkit new scratchpad <slug>` (paired with the `scratchpad-author` skill) to start one, `pkit scratchpad done <slug> --produced <ref>...` or `pkit scratchpad drop <slug>` to retire. The area README is the spec.
- **Git (COR-008).** Conventional commits format (`<type>(<scope>): <description>`); one logical unit per commit. See COR-008's body for the project's type list and branch-naming examples.
- **Versioning (PRJ-002).** Pre-1.0 hybrid bump policy: a PR bumps `.pkit/VERSION` if and only if it lands a *surface change* (new CLI command, new principle in an accepted COR, breaking change, new area / variant, schema change, new convention adopters follow). Non-surface (docs refinement, internal refactors, fixes that don't change behaviour, test additions, PRJ records) doesn't bump. Use `pkit version bump <segment>` for the bump (auto-broadens kit-shipped components' `requires_backbone`).
- **Migrations on surface changes (COR-010 / rules/core.md #7).** When the working diff includes a file/directory **rename or removal** in a kit-owned tree, a `schema_version` bump in a YAML schema, a breaking CLI signature change, or a capability subtree restructure — author a migration script at the affected tier (backbone / adapter / capability) **in the same commit or PR**. Before every commit that touches kit-owned trees, run `pkit migrations check-diff --include-working-tree --base main` to verify coverage; if it reports UNCOVERED, pause and author the migration before committing. The same check (without `--include-working-tree`) runs in CI on every PR — that's the safety net. Pure additions (new skill, new schema, new decision), docs refinements, and behaviour-preserving fixes don't trigger.

## Reviewer agents — invocation discipline (per COR-024)

Four reviewer agents form a structural-checks stack. Invoke them at the right stage; do not skip the upstream ones.

| Agent | When | Tooling |
|---|---|---|
| `critic` | **Before showing the user any substantive proposal** — a new or amended COR / PRJ / DEC / ADR, a multi-component design, a command-palette proposal, an architectural rework, a plan touching three or more files. Trivia and Q&A are exempt. Also: on user-demand for opposition, or for periodic adversarial sweeps. | Read-only. Returns structured critique (red flags / gaps / weak reasoning / counter-alternatives). Revise the proposal (or push back if the critique is wrong) before surfacing to the user. |
| `architect` | When the proposal touches the big picture — introduces a new abstraction or component, touches more than one capability or area, modifies a previously-accepted foundational decision, renames or relocates a kit-owned tree, or adds a cross-cutting concern (failure semantics, config-block growth, lifecycle taxonomy). Fire *after* `critic` has run. | Read + constrained Edit on overlay-resolved `<architecture-docs>` and `<adr-records>`. Returns architectural review + escalation flag when authorisation from the architectural perspective is needed. Advisory at v1 — does not refuse proposals. |
| `methodology-reviewer` | Once the artifact is authored — runs the disciplines audit (axiom / project-neutrality / principles-not-inventory / universal applicability / artifact-role placement). | Read-only. |
| `convention-compliance-reviewer` | At commit / PR time on the diff — conventional-commits format, no-shared-files, branch naming, surface-change discipline. | Read-only. |

Ordering when multiple apply on the same work: `critic` → `architect` → `methodology-reviewer` (on the authored artifact) → `convention-compliance-reviewer` (on the diff). Each catches a distinct failure mode; skipping upstream agents costs more than running them.

The default is to call them. Skipping is a deliberate choice (trivia exemption, no-cross-cutting-concern, no-artifact-authored-yet, no-diff-yet); state the exemption explicitly when skipping.

## Authoring tasks — invoke skills, not scripts

For authoring a kit-shipped artifact (decision, adapter, migration, area, scratchpad note, capability), **invoke the paired skill** rather than calling the underlying script directly. The skill carries the disciplines (axiom / project-neutrality / principles-not-inventory), the acceptance gate, the slug-choice judgement, and the body-drafting walkthrough; the script is just the deterministic stamp underneath.

Pairing per COR-005's "Skill / command pairing":

| Authoring task | Skill | Underlying command |
|---|---|---|
| New decision record | `decision-author` | `pkit new decision <namespace> <slug>` |
| New adapter | `adapter-author` | `pkit new adapter <name>` |
| New migration | `migration-author` | `pkit new migration --tier <tier> [...]` |
| New area | `area-author` | `pkit new area <name> [--variant <variant>]` |
| New scratchpad note | `scratchpad-author` | `pkit new scratchpad <slug>` |
| New agent | `agent-author` | `pkit new agent <namespace> <name>` |
| New storyboard | `storyboard-author` | `pkit new storyboard <artifact-kind> <name>` |
| New capability | `capability-author` | `pkit new capability <name>` |
| Work with schemas (new schema / add entry / rename entry / distill from upstream) | `schema` | `pkit new schema`, `pkit schemas add`, `pkit schemas rename` (composite per COR-020; sub-procedure picked inside the skill) |

If a skill doesn't exist for a task, invoke the script directly *and follow the disciplines manually* — read CONTRIBUTING.md's relevant section, pick the slug, and use the script for the stamp. Do not author by hand: that is what produced the wrong-number record in PR #16.

## Memory

Do **not** save patterns, feedback, or corrections into private memory. Anything worth remembering across sessions belongs in a project doc — `CLAUDE.md`, `CONTRIBUTING.md`, or the relevant area README — where it's visible to every author, human or agent.

