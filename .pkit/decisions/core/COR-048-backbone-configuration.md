---
id: COR-048
title: A project keeps its backbone declarations in one schema-checked file
status: accepted
date: 2026-09-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

Some facts about a project are not owned by any capability or agent, yet the backbone needs them. The project's name is one: anything the backbone reports about the project must not guess it from a folder or remote name. Configuration exists elsewhere, but each place has another owner:
- a capability keeps its own settings in its own subtree;
- the agent overlay (COR-013) exists so agent bodies can name project paths.

Neither is "what this project declares to the backbone".

The backbone already reads the project's name from a project-owned file. No core record defines that file, so a core record that wants to add a declaration has nothing to build on, and the file has no schema: a misspelt key is silently ignored.

## Decision

**A project keeps its declarations to the backbone in one project-owned configuration file. The backbone reads it, sync never touches it, and it is validated as a whole against a schema.**

1. **One file, owned by the project.** It holds project-level declarations the backbone reads. It sits in the project-owned part of the tree. It survives upgrade, sync, and uninstalling any capability or the tool itself, because none of them writes or removes it. Its location is documented in the CLI reference.

2. **Every key is owned by a record.** A key exists because a decision record introduced it, and that record defines the key's meaning, its default and who may write it.
   - **Core records** own the keys the backbone reads. This record takes ownership of the project-name key the backbone already reads.
   - **Project records** may own keys only under a reserved `project` block. That block is checked for being well-formed only; project-supplied schemas for it are deferred until a real need appears.
   - **Capabilities do not add keys.** Their settings stay in their own subtrees.
   - **Values that must reach every adopter of a distribution** do not belong here, because this file is never distributed.
   - **Keys naming installed components.** A core record may define a key whose entries name installed components, such as selecting which capability answers something. That record says how the entries are checked: against what is installed, not against a fixed list. It also says what happens when a named component is uninstalled. The uninstall offers to clear the entry with consent, and validation otherwise reports the stale entry with the fix.

3. **Absence means defaults.** A missing file, an empty file, or a missing key means the owning record's default applies. That is never an error unless the owning record says so.

4. **Strict when checked, forgiving when read.**
   - **Validation** (the methodology's validate command, and continuous integration) is strict. An unknown key is an error, reported with the nearest known key. So is a known key with an invalid value, and so is a file that does not parse.
   - **Commands that merely read** the file never fail because of it. On an unparsable file or an invalid value they warn and use the default. A typo is caught where checking happens and never blocks ordinary work.

5. **Written only with consent.** A key is written only by the writers its owning record names, such as a backbone command or a capability offering to record a value on install, and only with consent:
   - interactively, by asking once;
   - non-interactively, only when an explicit confirmation flag is given;
   - by an upgrade migration that the owning record specifies, where running the upgrade is the consent.

   With nobody to ask and no flag, nothing is written and the default applies.

6. **Keys change like any surface.** Adding a key is additive. Retiring or renaming one is a surface change and ships a migration (COR-010). Moving a project back to an older tool version that does not know a newer key requires removing that key first. The older tool's validation names it as an unknown key, possibly from a newer version.

7. **Adopts the existing file.** The file the backbone already reads for the project's name is this file. A project that has it keeps it unchanged; a project without it gains it only when a key is first written.

## Rationale

**Why one file, not a key in each consumer's config.** Declarations like the project's name or its documentation locations are facts about the project. Several parts of the backbone read them, and none of those parts owns them. Scattering them across consumers' settings would describe the same project several times over, and they would drift apart.

**Why not the agent overlay.** The overlay is a substitution mechanism for agent bodies at deploy time. Commands and checks are the ones that read backbone declarations, and they should not have to learn the overlay's resolution rules.

**Why not an area.** An area (COR-011) is a slice of the methodology with a README, a declared layout variant, and core and project parts. This is a single project-only file of declarations, with no core counterpart and no layout. Making it an area would add structure with nothing to hold.

**Why unknown keys are errors in validation, with a suggestion.** A misspelt key that silently falls back to a default is the failure a schema exists to prevent. A warning would also surface it, but warnings are routinely ignored, and the misspelling would keep silently disabling the intended setting. An error in validation, with the nearest known key suggested, catches it at the one moment it is cheap to fix. Keeping runtime reads forgiving (point 4) means the strictness never blocks ordinary commands. The only cost is on a downgrade, where point 6 makes the fix explicit.

**Why each key is owned by a record.** It keeps the file small and gives every key an answerable question: what does it mean, and who decided that? It also stops the file becoming a general settings bag.

### Alternatives considered

- **Keep defining the file only in the project-level decision that introduced it.** Rejected. Core records could not build on it, and it would never get a schema.
- **Put backbone declarations in the agent overlay.** Rejected. It stretches an agent-deploy mechanism into a general configuration store.
- **Let capabilities add keys here too.** Rejected. Ownership would blur, and a strict schema would be impossible without every capability contributing to it; capabilities already have their own configuration homes.
- **Tolerate unknown keys, or only warn on them.** Rejected. Misspellings would pass silently or be ignored as noise.
- **Fail every command on an invalid file.** Rejected. A typo in one key would break unrelated commands that only wanted to read a different key.

## Implications

- **A schema for the file** ships with the backbone and is run by validation. Each core record that introduces a key extends it. The `project` block is only checked for being well-formed.
- **The project-name key** is the schema's first entry.
- **Later core records** that need a project-level declaration add a key here rather than creating their own file.
- **Adding the schema is a surface change** adopters can see. Existing files and values are unaffected.
