---
reader: user
kind: signpost
pkit:
  friction:
    anchors:
      artefact:
        - .pkit/decisions/README.md#
        - .pkit/decisions/README.md#the-no-shared-files-invariant
        - .pkit/adapters/README.md#
        - .pkit/lifecycle/README.md#
        - .pkit/cli/README.md#
        - .pkit/cli/README.md#authoring-commands
        - .pkit/rules/README.md#
        - .pkit/skills/README.md#
        - .pkit/agents/README.md#
        - .pkit/schemas/README.md#
        - .pkit/process/README.md#
        - .pkit/scratchpad/README.md#
      record: [COR-011, COR-017]
    revalidated:
      at: 2026-10-16T14:21:51Z
      outcome: unchanged
      unchanged-because: The CLI reference's 'Authoring commands' gains a new capability entry, and the decisions README's 'The no-shared-files invariant' links the lifecycle README for the merge tier that asks nothing. This index only points to both sections, as where to start and how to author an area, adapter, capability or migration, so it holds.
---

# project-kit

`.pkit/` holds the methodology project-kit installs into your repository and keeps up to date, and your own records and rules beside it.

## Areas

- [`decisions/`](decisions/README.md) — your project's decision records: why each significant choice was made, apart from how it is implemented. They sit beside the methodology decisions project-kit ships.
- [`adapters/`](adapters/README.md) — the methodology's content translated for the AI harness you use, one adapter per harness.
- [`lifecycle/`](lifecycle/README.md) — how project-kit installs, updates and removes resources, and how versions evolve across the backbone and its components.
- [`cli/`](cli/README.md) — `pkit`, the command-line interface you use to install the methodology, pull updates, manage capabilities and check state.
- [`rules/`](rules/README.md) — operational rules and tool hygiene: the shipped ones in `core.md`, and your own in `project.md` beside it.
- [`skills/`](skills/README.md) — installable agent skills, which the adapter deploys into your AI harness: the conversational half of the authoring loop.
- [`agents/`](agents/README.md) — persistent roles AI tooling can be delegated to, each with its own scope, reading list, tools and behaviour.
- [`schemas/`](schemas/README.md) — the schemas mechanism: data files, each with a shape declaration, that hold rules and data apart from the code that reads them.
- [`process/`](process/README.md) — the shared process substrate: a content-free state machine that a discipline binds its staged, gated process to.
- [`scratchpad/`](scratchpad/README.md) — exploratory drafts for architectural questions too large for a record on first pass.

## Capabilities

- [`capabilities/`](capabilities/) — the capabilities your project installs, each an opt-in, self-contained unit of methodology with its own README (COR-017). They sit beside the areas, and are not areas (COR-011).

## Where to start

- **New to project-kit:** [`decisions/README.md`](decisions/README.md), and in it "The no-shared-files invariant", which governs the other areas too.
- **Looking for a command:** [`cli/README.md`](cli/README.md).
- **Authoring an area, adapter, capability or migration:** [`cli/README.md`, "Authoring commands"](cli/README.md#authoring-commands).
- **Upgrading project-kit in your project:** [`lifecycle/README.md`](lifecycle/README.md).
