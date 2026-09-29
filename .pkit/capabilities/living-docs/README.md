# living-docs capability

Keep your documentation **true for the people who read it**, even when an agent writes most of it. Documentation is organised into spaces by audience: user-facing docs for people who use the system, and technical docs for the people and agents who build it. Every page names its reader and is anchored to what makes it true. When those anchors change, drift is detected, and an agent proposes the fix for a person to review. The rule is in [living-docs:DEC-001-living-docs-discipline].

## How it works

- **Spaces.** A user space and a technical space, kept separate: neither root lies inside the other. You can add others. New pages go under each space's root. A space can also include places the project declares — inside a root, where they inherit that root's space, or outside every root, such as the repo's top-level README, where the capability's project configuration assigns them to a space. Where places nest the most specific one wins. Decision records, rule sets, and anything another capability claims are anchor targets or that capability's artefacts, never pages. Each space's *definition* (its rules and templates) lives in the technical space.
- **Rules.** A shared method rule set, `LDOC`, will ship with this capability. Each space adds its own rules on top (core rule sets, COR-051). What the rules require is in point 3 of the decision.
- **Anchors and friction.** Each page's anchors (code, decisions, sources, analysis artefacts) must ground everything it says. The core friction check (COR-050) flags a page when any of those changed and nobody revalidated it.
- **Proposals, never blind edits.** The agent proposes each fix with its evidence, and a person reviews it.
- **Reader-review.** The agent reads a page as its declared reader and reports what that reader would miss or wouldn't need.

## Connections (design-ahead)

Declared in the decision; the package metadata gains them with the first implementation increment. The capability provides the `pkit::documentation` role (COR-053); `pkit::` is this distribution's literal for the methodology's publisher qualifier ([the lifecycle README, "The methodology's literals"](../../lifecycle/README.md#the-methodologys-literals)).

- **Accepts** `pkit::documentation:readers`: who reads and what they need. It starts with a built-in `user` and `maintainer`. You can add or override readers in a [project file](../../lifecycle/README.md#where-a-project-filler-file-lives-the-address-to-path-mapping), and an analysis capability, such as software-analysis, can supply them too.
- **Accepts** `pkit::documentation:reading-evidence`: results of executed checks that follow the docs, such as a simulated user running a guide. Advisory.
- **Contributes** to `pkit::work-tracking:doc-check` with page friction and uncovered surface. Inert when no work-tracking capability is installed.

## Declaring your spaces

Where your documentation lives is declared in two files, joined by path:

- **The backbone configuration** (`.pkit/project/config.yaml`) names the two documentation roots (`docs.user`, `docs.internal`) and every place outside them that holds pages (`friction.places`), and the paths the friction checks leave out (`friction.exclude`). The CLI reference's "Configuration file" section documents those keys.
- **This capability's project configuration** (`.pkit/capabilities/living-docs/project/config.yaml`) holds what only living-docs needs: each space's entry point, and which space each place belongs to.

```yaml
pkit_schema: living-docs:config
schema_version: 1
spaces:
  user:      { entry-point: README.md }        # the page a user starts from
  technical: { entry-point: CONTRIBUTING.md }  # the page a maintainer starts from
places:                                        # place → space, the place written as in friction.places
  README.md: user
  CONTRIBUTING.md: technical
```

A place inside a root belongs to that root's space; list it under `places` only to assign it elsewhere. A place outside every root must be listed. Each place names exactly one space. The file's shape is `schemas/config.schema.json`, which `pkit validate` applies. Trees a sync copies into your repository are never places; in a repository where those trees are the authored source, they may be (the lifecycle README, "The ownership predicates"). The backbone's friction validation enforces this for every declared place, yours or a capability's, as its `synced-place` finding (the schemas README, "The friction block"), and this capability's place validation relies on that finding rather than checking a second time.

## Adopting it on an existing project

Onboarding is transformation, not moving files. The agent proposes which space each page belongs to, how pages should be split or rewritten for their readers, and which anchors each statement needs. Every proposal lands as a reviewable change.

## What's shipped now, what's next

This increment ships the decision, this README and the project configuration's schema (entry points and place assignment). Next come: the shared method rule set, page templates, the declarations of places, surface and connections, the validation of places and assignments, and the agent that proposes fixes and performs reader-review.

## Citing this capability's decisions

`[living-docs:DEC-001-living-docs-discipline]`.

## Dependencies

None. It works without analysis, work-tracking or testing capabilities, and each can enrich it.
