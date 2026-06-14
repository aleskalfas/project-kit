# project-kit

Methodology framework — installed into your repo, kept in sync as the methodology evolves.

This README maps `.pkit/`. Each area is a self-contained slice with its own README; pure navigation here, no methodology content of its own.

## Areas

| Area | What it does |
|---|---|
| [`decisions/`](decisions/README.md) | Architectural-decision record system. Two namespaces: `core/` (kit-shipped, COR-prefixed) and `project/` (yours, PRJ-prefixed). The no-shared-files invariant lives here. |
| [`capabilities/`](capabilities/) | Opt-in installable disciplines (per COR-017). Each capability ships its own README — `project-management/` (issue lifecycle, board state machine, PR conventions), `evidence/`, `software-engineering/`. Adopters install the ones they need. |
| [`adapters/`](adapters/README.md) | Translates kit content into the format and locations a specific AI harness expects (`claude-code` today). |
| [`lifecycle/`](lifecycle/README.md) | Packaging and dependency architecture: manifest schema, upgrade procedure, migration directory layout, register/unregister mechanics. |
| [`cli/`](cli/README.md) | The `pkit` command-line surface — `init`, `sync`, `merge`, `upgrade`, `bundle …`, `new …`, `status`, `validate`, `version`. |
| [`rules/`](rules/README.md) | Universal hard rules and tool hygiene patterns. Loaded by every adopter's `CLAUDE.md` via `@.pkit/rules/core.md` so agents see them at session start. |
| [`skills/`](skills/README.md) | Installable agent skills, harness-agnostic by design; deployed into the active harness by the adapter. The conversational / judgement-bearing half of authoring loops (per COR-006) — paired with the kit's authoring commands per COR-005. |
| [`agents/`](agents/README.md) | Agent definitions — persistent roles AI harnesses delegate against (per COR-013). Core ships universal reviewers (`critic`, `architect`, …); capabilities add their own. Deployed by the adapter. |
| [`schemas/`](schemas/README.md) | YAML schemas + JSON Schema companions — the structured source of truth capabilities read at runtime (per COR-018). |

## Where to start

- **New to the kit:** [`decisions/README.md`](decisions/README.md) — explains the foundational pattern (the no-shared-files invariant) that every other area inherits.
- **Looking for a command:** [`cli/README.md`](cli/README.md).
- **Authoring a capability, adapter, or migration:** [`cli/README.md`](cli/README.md) → "Authoring commands".
- **Upgrading the kit in your project:** [`lifecycle/README.md`](lifecycle/README.md).
