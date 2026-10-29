# Rule sets

The backbone's method rule sets ([COR-051](../decisions/core/COR-051-rule-sets.md)). A file here is a rule-set file because of where it is, and every Markdown file here but this one is read as a rule set the backbone ships, cited `backbone:<SET>` (the schemas README, "Rule-set files"). Sync refreshes the folder with the backbone, so a project never edits a file here. A project keeps its own rule sets under its internal documentation root.

- **`ops.md`** — `OPS`, the backbone's loaded set: core's operational rules, each with its permanent id, status and origin ([COR-068](../decisions/core/COR-068-loaded-rule-sets.md)). Core rule 19 is `backbone:RS-OPS-019`. Every session loads `.pkit/rules/core.md`, which `pkit rule-sets generate` writes from this set where it is authored. Edit the set, never the loaded file. The rules area's README says how the two relate.
