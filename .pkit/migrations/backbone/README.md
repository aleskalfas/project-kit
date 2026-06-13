# Backbone migrations

Per-version migration scripts for the kit's backbone, organised as `<major>.<minor>.0/<NNN>-<slug>.sh` (per COR-010 and `.pkit/lifecycle/README.md`).

Empty today — the backbone is at `0.1.0` (see `.pkit/VERSION`) with no prior version to migrate from. The first migration directory lands when the backbone reaches `0.2.0` (or later) and an upgrade requires a manifest-schema, structural, or resource-scoped migration.

Each version directory holds scripts that run when an adopter upgrades into that version's `<major>.<minor>` line. Within a directory, scope ordering is `manifest-schema → structural → resource-scoped`, by the `NNN` index within each scope. Patches don't have migrations (per the lifecycle spec — backward-compatible bug fixes by semver convention).
