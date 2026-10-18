# Backbone migrations

The backbone's migration scripts, one folder per version, as `<major>.<minor>.0/<NNN>-<slug>.sh` ([COR-010](../../decisions/core/COR-010-resource-lifecycle.md)). The spec is the lifecycle README's [migration framework](../../lifecycle/README.md#migration-framework).

- **When a folder runs:** a version transition runs each folder above the backbone version the project last completed, up to its target. A folder at or below a released version never runs for a project already there. So a new script goes in a folder no release has shipped.
- **The order within a folder:** the runner runs a folder's scripts in the order of their names, so the zero-padded number each name opens with sets the order. Each number is used once. A script that must run before another takes the lower number. COR-010's order of scopes follows from the numbers: manifest-schema first, then structural, then resource-scoped.
- **Adding a script:** `pkit new migration --tier backbone --name <slug>` picks the folder and the next number. `pkit migrations check-diff` fails a change that adds a script to a released folder, or with a number its folder already holds.
- **Patch releases** have no migrations. A folder covers every patch of its minor line.
