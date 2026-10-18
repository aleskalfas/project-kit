# Backbone migrations

The backbone's migration scripts, one folder per version, as `<major>.<minor>.0/<NNN>-<slug>.sh`. Your project receives them by sync, and a version transition runs them. [COR-010](../../decisions/core/COR-010-resource-lifecycle.md) sets the rules, and the lifecycle README's [migration framework](../../lifecycle/README.md#migration-framework) is the spec.

- **When a folder runs:** a version transition runs each folder above the backbone version the project last completed, up to its target. Where the project records no completed transition, it runs every folder up to the target once ([the replay](../../lifecycle/README.md#the-replay-a-missing-completion)).
- **The order within a folder:** the runner runs a folder's scripts in the order of their names. Each name opens with a zero-padded number, used once in its folder. The numbers follow COR-010's order of scopes: manifest-schema first, then structural, then resource-scoped.
- **Safe over any state:** a backbone migration acts only on a positive sign that its change is needed, since a transition may run it again over a project whose migration history is unknown.
- **Patch releases** have no migrations. A folder covers every patch of its minor line.

These scripts are the methodology's. Migrations for a component your project authors live with that component ([directory layout](../../lifecycle/README.md#directory-layout)).
