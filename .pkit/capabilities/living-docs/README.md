# living-docs capability

Keep your documentation **true for the people who read it**, even when an agent writes most of it. Documentation is organised into spaces by audience: user-facing docs for people who use the system, and technical docs for the people and agents who build it. Every page names its reader and is anchored to what makes it true. When those anchors change, drift is detected, and an agent proposes the fix for a person to review. The rule is in [living-docs:DEC-001-living-docs-discipline].

## How it works

- **Spaces.** A user space and a technical space, kept separate: neither root lies inside the other. You can add others. New pages go under each space's root. A space can also include declared places outside its root, such as the repo's top-level README. Each space's *definition* (its rules and templates) lives in the technical space.
- **Rules.** A shared method rule set, `LDOC`, will ship with this capability. Each space adds its own rules on top (core rule sets, COR-051). What the rules require is in point 3 of the decision.
- **Anchors and friction.** Each page's anchors (code, decisions, sources, analysis artefacts) must ground everything it says. The core friction check (COR-050) flags a page when any of those changed and nobody revalidated it.
- **Proposals, never blind edits.** The agent proposes each fix with its evidence, and a person reviews it.
- **Reader-review.** The agent reads a page as its declared reader and reports what that reader would miss or wouldn't need.

## Connections (design-ahead)

Declared in the decision; the package metadata gains them with the first implementation increment. The capability provides the `pkit::documentation` role (COR-053). `pkit::` is the methodology's publisher qualifier, written `<methodology>::` in the decision records.

- **Accepts** `pkit::documentation:readers`: who reads and what they need. It starts with a built-in `user` and `maintainer`. You can add or override readers in a project file, and an analysis capability, such as software-analysis, can supply them too.
- **Accepts** `pkit::documentation:reading-evidence`: results of executed checks that follow the docs, such as a simulated user running a guide. Advisory.
- **Contributes** to `pkit::work-tracking:doc-check` with page friction and uncovered surface. Inert when no work-tracking capability is installed.

## Adopting it on an existing project

Onboarding is transformation, not moving files. The agent proposes which space each page belongs to, how pages should be split or rewritten for their readers, and which anchors each statement needs. Every proposal lands as a reviewable change.

## What's shipped now, what's next

This increment ships the decision and this README. Next come: the shared method rule set, page templates, the declarations of places, surface and connections, and the agent that proposes fixes and performs reader-review.

## Citing this capability's decisions

`[living-docs:DEC-001-living-docs-discipline]`.

## Dependencies

None. It works without analysis, work-tracking or testing capabilities, and each can enrich it.
