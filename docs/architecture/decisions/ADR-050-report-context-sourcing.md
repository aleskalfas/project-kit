---
id: ADR-050
title: Report context sourcing — pm-provided workstream read-verb, declared project name, never paths
status: accepted
date: 2026-08-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

*How a report learns **which project and which workstream** it comes from without breaking two boundaries: the project name comes from a **declared** source (a project-config `name` key, fallback the git remote's repo name — never a filesystem path segment), and the workstream comes from a **pm-capability-provided read verb** dispatched through the capability dispatcher — the backbone never interprets pm's vocabulary directly. Both degrade to omission; nothing blocks a report.*

## Context

Reports gain a visible project + workstream context line + parseable marker (EPIC #634, the design carrier scratchpad). Two sourcing questions have architectural weight:

1. **Project identity.** The obvious sources are path-derived (directory basename) — which violates the redaction discipline (PRJ-008: paths never leave the machine; a basename is a path leaf) — or declared. Where does the declaration live, and what is the fallback chain?
2. **Workstream.** Workstream is **pm-capability vocabulary** (`workstreams.yaml`, the classification axes) — not a backbone concept. The natural derivation (current branch `<type>/<N>-<slug>` → issue #N → its workstream label) requires reading pm's labels. Backbone code interpreting a capability's vocabulary would be the codebase's first backbone→capability-vocabulary read — a layering inversion, even read-only. The established direction is one-way: capabilities plug into the backbone; the backbone knows capabilities only through backbone-owned metadata (the manifest).

## Decision

1. **Project name: declared, with a two-step fallback.** A `name` key in the adopter's project config is the source of truth; on first report without one, the compose flow **prompts once** and offers to write it. Fallback: the git remote's **repo name** (without the owner/org — an adopter's private org name is itself potentially sensitive; the confirm gate shows whatever is chosen either way). Never a filesystem path segment, including the directory basename. No name resolvable ⇒ the context line is omitted, stated as omitted in the composed body.
2. **Workstream: the backbone asks pm.** The pm capability ships a small **read verb** (context-workstream: resolve the current branch → issue → workstream, print one value or nothing); the backbone report compose invokes it **by subprocess through the existing capability-command dispatcher** (COR-021's pattern — the same mechanic every pm verb already uses), and treats it as optional: pm not installed, the verb absent, the branch not issue-shaped, or the issue unlabelled ⇒ workstream omitted. `--workstream <value>` on the report verbs overrides. The backbone never parses `workstreams.yaml`, never reads issue labels itself, and carries no knowledge of pm's schema.
3. **Both values are body content, not target-repo labels.** They render as the human context line + the `key=value` report marker (the #639 marker format, extended with `project=` / `workstream=`), and stamp into a reported scratchpad note's frontmatter at send time ([COR-043](../../../.pkit/decisions/core/COR-043-scratchpad-reported-state.md)). The upstream repo's label vocabulary is never touched.

## Rationale

- **Declared-over-derived for identity** is the redaction discipline extended from "strip paths" to "never *source* from paths": a value that never originates in a path cannot leak one. The prompt-once flow makes the declaration cheap; the repo-name fallback keeps zero-config reports useful.
- **The dispatcher subprocess keeps vocabulary knowledge where it lives.** Realization (ii) — a contained direct read of pm's files from backbone code — was weighed and rejected: even read-only it plants backbone code that breaks when pm's schema evolves, and it sets the inversion precedent. The subprocess seam costs one process spawn on compose (interactive-scale, negligible) and pm may change its internals freely behind the verb. A generic "context provider" plugin seam is over-engineering at one consumer (COR-007) — if a second capability ever wants to contribute report context, that recurrence funds the generalisation.
- **Degrade-to-omission everywhere** keeps the report channel's posture: context enriches, never gates; a bare report is always fileable.

### Alternatives considered

- **Directory basename as project name** — rejected: a path leaf by another name; violates never-source-from-paths.
- **Include the remote owner/org in the fallback name** — rejected as default (potentially sensitive); the declared `name` key can carry any form the adopter wants.
- **Backbone reads `workstreams.yaml` / issue labels directly** — rejected: layering inversion, schema coupling, precedent cost (above).
- **A generic context-provider seam** — rejected at one consumer; revisit on recurrence.
- **Context as upstream labels** — rejected: pollutes the target's label vocabulary with every adopter's taxonomy; body marker keeps it filterable without shared namespace.

## Implications

- The pm capability ships the `context-workstream` read verb (its own small surface — pm capability changeset; recorded in pm's docs, no new DEC needed: it is a read-only accessor implementing this ADR's seam).
- The backbone compose gains the prompt-once `name` flow + config key (config-block growth: one key, project-owned), the dispatcher invocation, the `--workstream` override, and the marker/frontmatter plumbing (#644's implementation).
- `report inbox --group-by project` becomes fully live once markers carry `project=` (the #639 implementation already parses `key=value` markers forward-compatibly).
- Coordinates with EPIC #411 (version provenance): one context block, extended — #411's fields join the same marker/line rather than adding a second block.
