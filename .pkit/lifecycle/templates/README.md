# Lifecycle templates

This folder holds no templates. The authoring commands (`pkit new adapter`, `pkit new capability`, `pkit new migration` and the others) keep theirs in the CLI's own scaffolding code, which ships with the CLI, so a release that changes a contract also changes what gets stamped (COR-005, "Authoring surface").

See `.pkit/cli/README.md`, "Authoring commands", for what each command stamps, and `.pkit/lifecycle/README.md` for the contract each stamp instantiates.
