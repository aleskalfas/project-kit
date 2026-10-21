---
TERM-acceptance-gate:
  name: acceptance gate
  status: active
  definition: "condition that work builds only on decision records and rules already accepted, never on proposed ones"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/decisions/README.md
        record:
          - COR-051#4
      revalidated:
        at: 2026-10-21T13:00:59Z
        outcome: unchanged
        unchanged-because: The decisions README gains how pkit refs lookup prints the file a record's id names. Which records bind, and the gate on proposed ones, are untouched.
TERM-adapter:
  name: adapter
  noun-forms: [adapters]
  status: active
  definition: "component that carries the methodology into one harness, translating its skills, agent definitions and permissions into what that harness reads"
  pkit:
    friction:
      anchors:
        record:
          - COR-005
          - COR-028
          - COR-047
      revalidated:
        at: 2026-10-20T01:37:01Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-agent-definition:
  name: agent definition
  noun-forms: [agent definitions]
  status: active
  definition: "document setting one standing remit with boundaries, what it reads and the paths it owns, deployed for a harness to delegate to"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/adapters/claude-code/deploy-agents.sh
        record:
          - COR-006
          - COR-013#1
          - COR-013#2
          - COR-013#5
      revalidated:
        at: 2026-10-20T01:37:02Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-anchor:
  name: anchor
  status: active
  definition: declared link from a document or a collection entry to what makes it true, such as a path, a record or another document or entry
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_discovery.py
        record:
          - COR-050#2
          - COR-050#7
      revalidated:
        at: 2026-10-20T01:37:04Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-answer:
  name: answer
  status: active
  definition: "statement in an artefact's `friction` block that settles an edit to what the artefact rests on, or a revisit its links ask for"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_write.py
        record:
          - COR-050#3
          - COR-050#4
      revalidated:
        at: 2026-10-20T01:37:05Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-area:
  name: area
  noun-forms: [areas]
  status: active
  definition: "top-level slice of a project's `.pkit/` tree, with a README declaring its layout, which needs no install: the methodology's areas, and any the project adds"
  pkit:
    friction:
      anchors:
        record:
          - COR-011
          - COR-003
      revalidated:
        at: 2026-10-20T01:37:06Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-artefact:
  name: artefact
  noun-forms: [artefacts]
  status: active
  definition: document with front matter, or keyed entry of a collection file, in a declared place, which carries its own anchors
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_discovery.py
        record:
          - COR-050#1
      revalidated:
        at: 2026-10-20T01:37:07Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-artefact-type:
  name: artefact type
  noun-forms: [artefact types]
  status: active
  definition: "declared name of what a document or collection entry is, given by the place holding its file, which a rule set's scope may select by"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_discovery.py
        record:
          - COR-056#1
          - COR-056#2
          - COR-056#3
          - COR-056#5
      revalidated:
        at: 2026-10-20T01:37:08Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-backbone:
  name: backbone
  status: active
  definition: "part of the system that ships whole at one version: the CLI, the core records and the engines"
  pkit:
    friction:
      anchors:
        record:
          - COR-010
          - COR-059#1
      revalidated:
        at: 2026-10-20T01:37:10Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-backbone-configuration:
  name: backbone configuration
  status: active
  definition: "project-owned file, never written by sync, holding the declarations the system reads, each key owned by a decision record, all checked by validation"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/project_config.py
          - src/project_kit/config_validate.py
        record:
          - COR-048#1
          - COR-048#2
          - COR-048#4
          - COR-048#5
      revalidated:
        at: 2026-10-20T01:37:11Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-base:
  name: base
  status: active
  definition: branch or other reference a check compares a change with, from the commit where the change's branch left it
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/default_branch.py
        record:
          - COR-054#2
          - COR-054#3
      revalidated:
        at: 2026-10-20T01:37:12Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-capability:
  name: capability
  noun-forms: [capabilities]
  status: active
  definition: "component that packages one discipline as decision records, skills, agent definitions, scripts and schemas, which each project chooses to install or not"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/capabilities.py
        record:
          - COR-017
          - COR-026
          - COR-031
      revalidated:
        at: 2026-10-20T01:37:13Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-change:
  name: change
  status: active
  definition: "unit of work that lands on the branch it targets"
  pkit:
    friction:
      anchors:
        record:
          - COR-009#1
          - COR-009#5
          - COR-050#3
          - COR-050#6
      revalidated:
        at: 2026-10-20T01:37:14Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-change-check:
  name: change check
  noun-forms: [change checks]
  status: active
  definition: "comparison of a head with its base, which finds the friction and dead anchors a diff brings, and lists every answer the diff wrote"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_check.py
        record:
          - COR-050#6
          - COR-050#12
          - COR-054#3
      revalidated:
        at: 2026-10-20T01:37:16Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-changeset:
  name: changeset
  noun-forms: [changesets]
  status: active
  definition: file naming the backbone or a component, the version segment a change moves it by, and a note for the changelog
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/changesets.py
        record:
          - PRJ-002#D1
          - PRJ-002#D2
      revalidated:
        at: 2026-10-20T01:37:17Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-component:
  name: component
  noun-forms: [components]
  status: active
  definition: "part of the system, versioned apart from the backbone, that declares which backbone versions it works with"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/manifest.py
          - src/project_kit/changesets.py
        record:
          - COR-010
      revalidated:
        at: 2026-10-20T01:37:18Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-component-origin:
  name: component origin
  status: active
  definition: "property the manifest records for an installed capability or adapter: shipped by its distribution, authored in the project, or supplied by an external source"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/manifest.py
        record:
          - COR-031#D1
          - COR-031#D2
          - COR-041
          - COR-059#1
      revalidated:
        at: 2026-10-20T01:37:19Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-connection-point:
  name: connection point
  noun-forms: [connection points]
  status: active
  definition: "declared interface that one installed capability defines and other components fill, depend on or subscribe to, without naming that capability"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/connections.py
        record:
          - COR-053#2
          - COR-053#3
          - COR-053#5
          - COR-053#6
      revalidated:
        at: 2026-10-20T01:37:20Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-consent:
  name: consent
  status: active
  definition: "person's agreement to a write, given by a reply when asked, an explicit confirmation flag, or running a command that a record says carries it"
  pkit:
    friction:
      anchors:
        record:
          - COR-048#5
          - COR-059#4
          - COR-002
      revalidated:
        at: 2026-10-20T01:37:22Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-data-point:
  name: data point
  noun-forms: [data points]
  status: active
  definition: "declared interface through which a role's provider accepts input, filled by project files, installed capabilities and the provider's own default, which the backbone resolves"
  replaces:
    - slot
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/data_points.py
        record:
          - COR-052#1
          - COR-052#2
          - COR-052#3
          - COR-052#6
          - COR-053#2
          - COR-061#1
      revalidated:
        at: 2026-10-20T01:37:24Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-debt:
  name: debt
  status: active
  definition: "stale or deferred finding of the whole-repository check, dated from the commit it originates in: the change nobody answered, or the deferral"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_repository.py
          - src/project_kit/friction_report.py
        record:
          - COR-050#9
      revalidated:
        at: 2026-10-20T01:37:25Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-decision-record:
  name: decision record
  noun-forms: [decision records]
  status: active
  definition: "document stating one choice among alternatives, with its context and reasons, numbered in its namespace and binding only once accepted"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/decisions.py
        record:
          - COR-006
          - COR-025
          - COR-058#1
      revalidated:
        at: 2026-10-20T01:37:26Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-default-branch:
  name: default branch
  status: active
  definition: "line of history where a project's changes land, `main` unless its backbone configuration names another, which every reader resolves from the shared remote's copy"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/default_branch.py
        record:
          - COR-008
          - COR-054#1
          - COR-054#2
          - COR-054#4
      revalidated:
        at: 2026-10-20T01:37:28Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-distribution:
  name: distribution
  noun-forms: [distributions]
  status: active
  definition: "edition of the methodology and of the system that carries it, released from one source repository through one channel"
  pkit:
    friction:
      anchors:
        record:
          - COR-041
          - PRJ-004
          - ADR-047#3
      revalidated:
        at: 2026-10-20T01:37:29Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-documentation-root:
  name: documentation root
  noun-forms: [documentation roots]
  status: active
  definition: "folder for internal or for user-facing readers, `docs/` unless the backbone configuration names another, from which locations for documents are derived unless set explicitly"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/docs_roots.py
        record:
          - COR-049#1
          - COR-049#3
          - COR-049#5
      revalidated:
        at: 2026-10-20T01:37:30Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-finding:
  name: finding
  noun-forms: [findings]
  status: active
  definition: "statement a check or a reviewer reports on what it judged, whose severity or kind says whether it fails the check or withholds an approval"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/validators.py
        record:
          - COR-050#12
          - COR-055#4
          - COR-055#5
          - COR-057#3
      revalidated:
        at: 2026-10-20T01:37:31Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-friction:
  name: friction
  status: active
  definition: finding that something an artefact rests on changed, such as an anchor's target or the anchor list, with no answer standing for it
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_check.py
          - src/project_kit/friction_repository.py
        record:
          - COR-050#1
          - COR-050#5
          - COR-050#6
          - COR-050#9
      revalidated:
        at: 2026-10-20T01:37:32Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-harness:
  name: harness
  status: active
  definition: "external tool that hosts the sessions of AI agents and runs their tool calls"
  pkit:
    friction:
      anchors:
        record:
          - COR-006
          - COR-047
      revalidated:
        at: 2026-10-20T01:37:34Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-head:
  name: head
  status: active
  definition: "latest commit of the branch that carries a change, the later state a check compares with the base"
  pkit:
    friction:
      anchors:
        record:
          - COR-050#5
          - COR-050#6
      revalidated:
        at: 2026-10-20T01:37:35Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-install:
  name: install
  status: active
  definition: "operation that adds the backbone or a component to a repository, after checking name collisions"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/install.py
          - src/project_kit/capabilities.py
        record:
          - COR-010
          - COR-017
          - COR-030
      revalidated:
        at: 2026-10-20T01:37:36Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-manifest:
  name: manifest
  status: active
  definition: "file where a project records what it installed, and at which version, kept for the backbone and for each shipped component"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/manifest.py
        record:
          - COR-010
          - COR-031#D2
          - COR-059#1
          - ADR-065#2
      revalidated:
        at: 2026-10-20T01:37:37Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-merge-delivery:
  name: merge delivery
  status: active
  definition: "operation that adds the methodology's baseline entries to a project-owned file and restores its safety entries, never removing an entry the project wrote"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/merge.py
        record:
          - COR-002
          - COR-059#2
      revalidated:
        at: 2026-10-20T01:37:39Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-methodology:
  name: methodology
  status: active
  definition: body of decision records, rules, operational rules and conventions the system ships and enforces
  pkit:
    friction:
      unanchored-because: It names the whole body the system ships, so an anchor on its records and rules would match every change to them. COR-007 says what a methodology is in general, not what this word names here.
      revalidated:
        at: 2026-10-20T01:37:40Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-migration:
  name: migration
  noun-forms: [migrations]
  status: active
  definition: script that carries a project's state across a version of the backbone or of a component
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/migrations.py
          - .pkit/capabilities/project-management/migrations/0.55.0/001-pm-reviewer-agent-rename.sh
        record:
          - COR-010
      revalidated:
        at: 2026-10-20T01:37:41Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-operational-rule:
  name: operational rule
  noun-forms: [operational rules]
  status: active
  definition: "instruction every AI agent session loads through the harness's include, numbered in the system's file or the repository's own, with no id, origin or status"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/adapters/claude-code/merge-claude-md.sh
        record:
          - COR-014
          - COR-051#1
      revalidated:
        at: 2026-10-20T01:37:42Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-package-metadata:
  name: package metadata
  status: active
  definition: "file a component ships that declares its version and ranges, and what it adds to the backbone, such as places, types, roles, commands and validators"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/package_validate.py
        record:
          - COR-017
          - COR-021
          - COR-053#3
          - COR-056#2
      revalidated:
        at: 2026-10-20T01:37:44Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-place:
  name: place
  status: active
  definition: path or glob the project or a component declares, within which the backbone looks for documents that carry anchors
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_discovery.py
        record:
          - COR-050#1
          - COR-050#14
      revalidated:
        at: 2026-10-20T01:37:45Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-point:
  name: point
  other-senses: [revalidation point, deferral point]
  status: active
  definition: "numbered or labelled part of a decision record's Decision, whose id names it for good once the record writes it as a heading"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/record_points.py
        record:
          - COR-058#1
          - COR-058#3
          - COR-058#4
      revalidated:
        at: 2026-10-20T01:37:46Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-project:
  name: project
  status: active
  definition: "repository the system is installed into, holding the methodology's files beside content of its own"
  pkit:
    friction:
      anchors:
        record:
          - COR-001
          - COR-010
      revalidated:
        at: 2026-10-20T01:37:47Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-project-owned-content:
  name: project-owned content
  status: active
  definition: "files the methodology does not own in an installed repository, which sync never removes and the system writes only through writers records name"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/lifecycle/ownership.py
        record:
          - COR-001
          - COR-003
          - COR-059#2
      revalidated:
        at: 2026-10-20T01:37:48Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-propagation:
  name: propagation
  status: active
  definition: "operation that writes the methodology's files into a project verbatim, at the recorded versions or a transition's target, over whatever stands at those paths"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/sync.py
        record:
          - COR-001
          - COR-059#2
          - ADR-065#1
      revalidated:
        at: 2026-10-20T01:37:50Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-pull-request:
  name: pull request
  noun-forms: [pull requests]
  status: active
  definition: "proposal on the hosting service to land one change on a target branch, reviewed there and merged, by default, as one squash commit"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/pull_request_landing.py
        record:
          - COR-009#1
          - COR-009#2
          - COR-009#3
          - COR-009#5
      revalidated:
        at: 2026-10-20T01:37:51Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-range:
  name: range
  status: active
  definition: set of versions of the backbone or of another capability that a component declares it works with, from a floor to any upper bound
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/versioning.py
        record:
          - PRJ-002#D4
          - COR-010
          - COR-030
      revalidated:
        at: 2026-10-20T01:37:52Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-recorded-version:
  name: recorded version
  noun-forms: [recorded versions]
  status: active
  definition: "number or ref a project keeps for the backbone or an installed component, naming the content it holds"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/manifest.py
        record:
          - COR-059#1
          - COR-059#2
          - COR-059#6
          - ADR-065#2
      revalidated:
        at: 2026-10-20T01:37:53Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-release:
  name: release
  status: active
  definition: "set of versions shipped together, named by its backbone version: one of the backbone, and one of each component shipped with it"
  pkit:
    friction:
      anchors:
        record:
          - COR-059#1
          - COR-059#7
          - PRJ-004
      revalidated:
        at: 2026-10-20T01:37:55Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-release-step:
  name: release step
  noun-forms: [release steps]
  status: active
  definition: "procedure that consumes every pending changeset and writes the new versions, raised floors, widened bounds and changelog entries, which land only on the default branch"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/release.py
        record:
          - PRJ-002#D3
          - PRJ-002#D4
          - PRJ-004
      revalidated:
        at: 2026-10-20T01:37:56Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-report:
  name: report
  status: active
  definition: "issue an adopter composes with the system and files on the repository of the distribution they use: a bug, a change request or feedback"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/report.py
        record:
          - PRJ-008
          - ADR-047#3
          - COR-043#3
      revalidated:
        at: 2026-10-20T01:37:57Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-reviewer:
  name: reviewer
  noun-forms: [reviewers]
  status: active
  definition: "AI agent or person, not the author, who reports on a draft or a change within a remit, leaving each fix to the author"
  pkit:
    friction:
      anchors:
        record:
          - COR-024
          - COR-050#3
          - COR-057#1
          - COR-057#3
          - COR-057#5
      revalidated:
        at: 2026-10-20T01:37:58Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-role:
  name: role
  noun-forms: [roles]
  status: active
  definition: "name, qualified by the publisher that coined it, under which one installed capability provides connection points others use without naming that capability"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/connections.py
        record:
          - COR-053#1
          - COR-053#7
      revalidated:
        at: 2026-10-20T01:38:00Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-rule:
  name: rule
  other-senses: [core rule, project rule]
  status: active
  definition: "statement, under a permanent id and with a recorded origin, that every document or collection entry it binds on must satisfy once accepted"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/rule_sets.py
        record:
          - COR-051#1
          - COR-051#3
          - COR-051#4
          - COR-051#5
      revalidated:
        at: 2026-10-20T01:38:01Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-rule-set:
  name: rule set
  noun-forms: [rule sets]
  status: active
  definition: "collection file of named statements that artefacts must satisfy, with its own version, the collections of its kind it inherits, and any scope selecting artefacts"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/rule_sets.py
        record:
          - COR-051#2
          - COR-051#6
          - COR-051#7
      revalidated:
        at: 2026-10-20T01:38:02Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-seeding:
  name: seeding
  status: active
  definition: "operation that creates a declared seed path from its template where the path is missing, at first install and at each backbone transition"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/install.py
          - src/project_kit/upgrade.py
        record:
          - COR-001
          - COR-003
          - COR-059#8
      revalidated:
        at: 2026-10-20T01:38:03Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-skill:
  name: skill
  noun-forms: [skills]
  status: active
  definition: "document holding a procedure that an AI agent loads for a matching task, deployed where the harness looks"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/adapters/claude-code/deploy-skills.sh
        record:
          - COR-005
          - COR-006
          - COR-020
      revalidated:
        at: 2026-10-20T01:38:05Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-source-repository:
  name: source repository
  noun-forms: [source repositories]
  status: active
  definition: "versioned tree where the backbone or a component is authored, whose files are the originals that synced copies elsewhere come from"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/lifecycle/ownership.py
        record:
          - COR-050#14
          - COR-041
          - ADR-059#1
      revalidated:
        at: 2026-10-20T01:38:06Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-stamp:
  name: stamp
  status: active
  definition: "authoring command that writes a new file with its id, front matter and location right, paired with the skill that carries its disciplines"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/scaffolds.py
        record:
          - COR-005
      revalidated:
        at: 2026-10-20T01:38:07Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-surface-change:
  name: surface change
  noun-forms: [surface changes]
  status: active
  definition: alteration of the system that an adopter could observe, depend on or break against
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/release.py
        record:
          - PRJ-002#D1
          - PRJ-002#D2
          - COR-050#8
      revalidated:
        at: 2026-10-20T01:38:08Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-sync:
  name: sync
  status: active
  definition: "operation that runs propagation at a project's recorded versions and regenerates what derives from its declarations, moving no version and running no migration"
  replaces:
    - reconciliation
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/sync.py
        record:
          - COR-001
          - COR-059#2
          - COR-059#9
      revalidated:
        at: 2026-10-20T01:38:10Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-synced-copy:
  name: synced copy
  noun-forms: [synced copies]
  status: active
  definition: "file that propagation writes into a project from the methodology or an externally-sourced component, and that the project never edits"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/lifecycle/ownership.py
        record:
          - COR-001
          - COR-050#14
          - COR-059#2
          - COR-041
      revalidated:
        at: 2026-10-20T01:38:11Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-system:
  name: system
  status: active
  definition: software under discussion, which you install, run and extend
  pkit:
    friction:
      unanchored-because: It names the whole of pkit, so an anchor on its code would match every change. No record defines it.
      revalidated:
        at: 2026-10-20T01:38:12Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-validation:
  name: validation
  status: active
  definition: "check of a project's own files against the invariants its records own, which installed components join through validators, failing on one severity alone"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/validate.py
        record:
          - COR-055#1
          - COR-055#2
          - COR-055#3
          - COR-055#5
      revalidated:
        at: 2026-10-20T01:38:13Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-version:
  name: version
  noun-forms: [versions]
  other-senses: ["data point's version"]
  status: active
  definition: "number of the form major.minor.patch that names one state of a top-level part of the system, as semantic versioning reads it"
  pkit:
    friction:
      anchors:
        record:
          - COR-010
          - PRJ-002#D2
      revalidated:
        at: 2026-10-20T01:38:15Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-version-pin:
  name: version pin
  noun-forms: [version pins]
  status: active
  definition: "project-owned file naming the release whose system runs the project's commands instead of the installed one, while that release can be fetched"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/router.py
        record:
          - ADR-049#1
          - ADR-049#2
          - ADR-049#3
          - ADR-064#1
          - ADR-064#3
      revalidated:
        at: 2026-10-20T01:38:16Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-version-transition:
  name: version transition
  noun-forms: [version transitions]
  status: active
  definition: "operation that moves a project's recorded versions to a target, running every pending migration and recording its completion only after they have run"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/upgrade.py
        record:
          - COR-059#3
          - COR-059#4
          - COR-059#6
          - COR-059#7
      revalidated:
        at: 2026-10-20T01:38:17Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
TERM-whole-repository-check:
  name: whole-repository check
  status: active
  definition: "comparison of every artefact at the latest commit with its revalidation point, which never fails"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_repository.py
        record:
          - COR-050#6
          - COR-050#9
      revalidated:
        at: 2026-10-20T01:38:19Z
        outcome: unchanged
        unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/glossary.md, with its entry and its section as they were, so its definition still holds.
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

## TERM-acceptance-gate — acceptance gate

Explained in [VIEW-the-system-and-its-methodology](domain-model/010-the-system-and-its-methodology.md#acceptance-gate).

**Example:** a [change](#term-change--change) would build on a [project](#term-project--project) record that is still proposed, so the change's author has the record accepted first, or pauses the change.

**Distinctions:**

- **Acceptance:** a record's or a [rule](#term-rule--rule)'s status moved from `proposed` to `accepted` in a reviewed change. Where that path involves a person, the person's review accepts the record or the rule (COR-051 [point](#term-point--point) 4).
- **Merge gate:** the checks and approvals a [pull request](#term-pull-request--pull-request) waits for before it merges (project-management DEC-028). It judges a change, not what the change builds on.
- **A process's gate:** a condition on one move of a subject between states (COR-033 P4).

## TERM-adapter — adapter

Explained in [VIEW-parts-of-the-system](domain-model/020-parts-of-the-system.md#adapter).

**Example:** the `claude-code` adapter links each [skill](#term-skill--skill) under `.claude/skills/`, and merges the [methodology](#term-methodology--methodology)'s permission entries into `.claude/settings.json`.

**Distinctions:**

- **Harness:** the external tool an adapter serves. A [harness](#term-harness--harness) is no part of the [system](#term-system--system).
- **Support declaration:** an adapter's grading of how far its harness meets each requirement the methodology states (COR-047 [point](#term-point--point) 2).
- **Realizer:** COR-028's name for an adapter as it enforces the permission model in its harness.

## TERM-agent-definition — agent definition

Explained in [VIEW-parts-of-the-system](domain-model/020-parts-of-the-system.md#agent-definition).

**Example:** `critic.md` is the critic's agent definition, which the main session dispatches before it shows a person a substantive draft.

**Distinctions:**

- **AI agent:** the runtime that runs an agent definition, or works as the main session under none (`ACT-ai-agent`). COR-006 and COR-013 call the definition itself an agent.
- **Skill:** a procedure an AI agent loads for a task. An agent definition sets the remit the agent works within (COR-006).
- **Overlay:** the project-owned file whose paths fill each placeholder of an agent definition when the [adapter](#term-adapter--adapter) deploys it (COR-013 [point](#term-point--point) 5).

## TERM-anchor — anchor

Explained in [VIEW-artefacts-and-friction](domain-model/070-artefacts-and-friction.md#anchor).

**Example:** `.pkit/release/README.md` anchors `src/project_kit/changesets.py`, so a [change](#term-change--change) that edits that file asks the page whether it still holds.

**Distinctions:**

- **Citation:** a record or a file that a document names in its text. A change to it asks the document nothing, unless an anchor names it too.
- **Dead anchor:** an anchor that resolves to nothing, such as a glob that matches no file. It is an error, never silence (COR-050 [point](#term-point--point) 7).
- **Registered kind:** a kind of anchor a [capability](#term-capability--capability) adds, with the command that resolves it. The [backbone](#term-backbone--backbone) resolves paths, records and [artefacts](#term-artefact--artefact) itself (COR-050 point 2).

## TERM-answer — answer

Explained in [VIEW-artefacts-and-friction](domain-model/070-artefacts-and-friction.md#answer).

**Example:** a [change](#term-change--change) renames a flag that a page describes, so the developer updates the page in the same change and revalidates it `updated`.

**Distinctions:**

- **Revalidation:** an answer saying the [artefact](#term-artefact--artefact) was reviewed against the change. It is `updated`, its content changed with it, or `unchanged`, with why it still holds (COR-050 [point](#term-point--point) 3).
- **Deferral:** an answer that puts off one [anchor](#term-anchor--anchor)'s [friction](#term-friction--friction), with a reason naming the follow-up that will answer it (COR-050 point 4).
- **Revisit entry:** an answer on a link's source, saying why a target still stands or which follow-up will revisit it (COR-050 point 16).
- **The list of answers:** the [change check](#term-change-check--change-check)'s list of every answer a change wrote, word for word, which a [reviewer](#term-reviewer--reviewer) works from (COR-050 point 3). The answers themselves live on the artefacts.
- **A command's answer:** what a resolver or a validator returns to the check that runs it. A missing one fails that check, and is no artefact's answer.

## TERM-area — area

Explained in [VIEW-capabilities-areas-and-connection-points](domain-model/030-capabilities-areas-and-connection-points.md#area).

**Example:** `.pkit/decisions/` is an area, whose `core/` folder holds the core records and whose `project/` folder holds the [project](#term-project--project)'s own.

**Distinctions:**

- **Capability:** an opt-in subtree beside the areas, which a project installs and may uninstall (COR-011).
- **Functional area:** a group of use cases in the analysis, such as `change` or `release` (software-analysis DEC-001 [point](#term-point--point) 2). It is no folder of the [methodology](#term-methodology--methodology).
- **An area of the project's own:** [project-owned content](#term-project-owned-content--project-owned-content), which [sync](#term-sync--sync) never touches (COR-011).

## TERM-artefact — artefact

Explained in [VIEW-artefacts-and-friction](domain-model/070-artefacts-and-friction.md#artefact).

**Example:** each use case of the analysis is an artefact, and so is each entry of this glossary, a collection file. So is each page project-kit lists in `friction.places`, such as `.pkit/cli/README.md`.

**Distinctions:**

- **Decision record:** an artefact only where a [place](#term-place--place) holds it (COR-050 [point](#term-point--point) 1). A record [anchor](#term-anchor--anchor) names a record whether or not a place holds it.
- **Held document:** a file a [component](#term-component--component) keeps in a folder it declares, such as a log of its reviews. It is never an artefact, even inside a place (COR-050 point 1).

## TERM-artefact-type — artefact type

Explained in [VIEW-artefacts-and-friction](domain-model/070-artefacts-and-friction.md#artefact-type).

**Example:** the glossary's [place](#term-place--place) gives each entry the type `software-analysis:term`, so `ANA`'s scope selects every term without naming a path.

**Distinctions:**

- **Kind field:** one of an [artefact](#term-artefact--artefact)'s own fields, naming a variety of its type, such as a page's `kind` (COR-056 points 2 and 4).
- **A rule's type:** every [rule](#term-rule--rule) is `backbone:rule`, whatever place holds its file (COR-056 [point](#term-point--point) 3).
- **Commit type and issue type:** a conventional commit's prefix (COR-008), and project-management's classification of an issue. They share only the word.
- **Friction:** never reads a type, so giving a place a type flags nothing (COR-056 point 5).

## TERM-backbone — backbone

Explained in [VIEW-parts-of-the-system](domain-model/020-parts-of-the-system.md#backbone).

**Example:** backbone 1.149.0 is one [version](#term-version--version) of the CLI, the core records and the [friction](#term-friction--friction) and [validation](#term-validation--validation) engines, released together.

**Distinctions:**

- **Component:** a part of the [system](#term-system--system) with a version of its own, which declares the backbone versions it works with. The backbone depends on no [component](#term-component--component) (COR-010).
- **Core:** no single thing in the analysis. The word names four things:
  - the backbone, the part
  - a core record, one of the backbone's [decision records](#term-decision-record--decision-record)
  - an [area](#term-area--area)'s `core/` folder, which holds the [methodology](#term-methodology--methodology)'s files
  - COR-001's core layer, the methodology as the side that ships content and writes into a [project](#term-project--project)
- **Methodology:** the body of decision records, rules, [operational rules](#term-operational-rule--operational-rule) and conventions the system ships and enforces. The backbone carries the part every project gets, and each [capability](#term-capability--capability) carries one part more.

## TERM-backbone-configuration — backbone configuration

Explained in [VIEW-a-projects-own-files](domain-model/050-a-projects-own-files.md#backbone-configuration).

**Example:** project-kit's `.pkit/project/config.yaml` declares its [documentation roots](#term-documentation-root--documentation-root) and its [friction](#term-friction--friction) mode and places, and leaves its [default branch](#term-default-branch--default-branch) at `main`.

**Distinctions:**

- **A capability's own configuration:** kept in the [capability](#term-capability--capability)'s own subtree. A capability adds no key to the backbone configuration (COR-048 [point](#term-point--point) 2).
- **Manifest:** what the [project](#term-project--project) installed, and at which [versions](#term-version--version). The backbone configuration holds what the project declares.
- **The harness's settings:** files such as `.claude/settings.json`, which the [harness](#term-harness--harness) reads and [merge delivery](#term-merge-delivery--merge-delivery) adds to.

## TERM-base — base

Explained in [VIEW-changes-review-and-releases](domain-model/060-changes-review-and-releases.md#base).

**Example:** CI names the [pull request](#term-pull-request--pull-request)'s target in `PKIT_CHECK_BASE`, so that target is each check's base. Each compares the [change](#term-change--change) from where its branch left the target.

**Distinctions:**

- **Default branch:** the base of every check that names no other. A base named for one run replaces it for that run only, and never changes it (COR-054 [point](#term-point--point) 3).
- **Where the branch left it:** the commit a check measures the change from, git's merge-base of the branch and the base. The base itself may have moved on since.
- **A pull request's base:** the hosting service's name for the branch a pull request targets. The analysis calls that branch the pull request's target, and CI names it as the checks' base.

## TERM-capability — capability

Explained in [VIEW-capabilities-areas-and-connection-points](domain-model/030-capabilities-areas-and-connection-points.md#capability).

**Example:** an adopter installs the `software-analysis` capability, which brings the analysis's stamps and checks and the method [rule set](#term-rule-set--rule-set) `SAN`.

**Distinctions:**

- **Area:** a slice of the [methodology](#term-methodology--methodology) that every [project](#term-project--project) holds, with no [install](#term-install--install) of its own (COR-011).
- **Adapter:** the other kind of [component](#term-component--component), which carries what one [harness](#term-harness--harness) needs and no discipline (COR-027).
- **Bundle:** a retired kind of package inside an [area](#term-area--area). A capability expresses its alternatives as data instead (COR-027).
- **Role:** what a capability provides for others to use without naming it, such as documentation (COR-053 [point](#term-point--point) 1).

## TERM-change — change

Explained in [VIEW-changes-review-and-releases](domain-model/060-changes-review-and-releases.md#change).

**Example:** the developer's change adds a command and revalidates the page that describes it. The change declares a [changeset](#term-changeset--changeset), then lands in one [pull request](#term-pull-request--pull-request).

**Distinctions:**

- **Surface change:** an alteration that an adopter could observe, depend on or break against. A change that makes one declares it in a changeset.
- **An alteration:** written with the verb, as in "what an [anchor](#term-anchor--anchor) stands on changed", or with *edit*. The noun names the unit of work.
- **Commit:** one step of a change on its branch. A change that lands through a pull request lands as one squash commit (COR-009 [point](#term-point--point) 1).

## TERM-change-check — change check

Explained in [VIEW-artefacts-and-friction](domain-model/070-artefacts-and-friction.md#change-check).

**Example:** `pkit friction check` reports `.pkit/release/README.md` until a branch that edits `src/project_kit/release.py` revalidates the page.

**Distinctions:**

- **Whole-repository check:** measures every [artefact](#term-artefact--artefact) from its own revalidation point at the latest commit, and never fails (COR-050 points 6 and 12).
- **Warning or enforcing:** in warning mode the change check reports and passes, and in enforcing mode it fails. It binds once CI requires it (COR-050 [point](#term-point--point) 12).
- **The list of answers:** the answers that the change check reports a [change](#term-change--change) wrote, word for word, which a [reviewer](#term-reviewer--reviewer) works from (COR-050 point 3).

## TERM-changeset — changeset

Explained in [VIEW-changes-review-and-releases](domain-model/060-changes-review-and-releases.md#changeset).

**Example:** a [change](#term-change--change) adds a command to the `software-analysis` [capability](#term-capability--capability), so the developer adds a changeset naming `software-analysis` and `minor`.

**Distinctions:**

- **Version:** a branch never edits a [version](#term-version--version) number, and declares its change in a changeset instead (PRJ-002 D1).
- **Segment:** the changeset's `kind`, one of `patch`, `minor`, `major` and `none`. It is a person's judgement of the change's surface, never read from the commit type (PRJ-002 D2).

## TERM-component — component

Explained in [VIEW-parts-of-the-system](domain-model/020-parts-of-the-system.md#component).

**Example:** the `software-analysis` [capability](#term-capability--capability) is a component, so a [change](#term-change--change) to its scripts declares a [changeset](#term-changeset--changeset) that names it.

**Distinctions:**

- **Backbone:** the part every component depends on, released whole at one [version](#term-version--version) of its own (COR-010).
- **A changeset's `component`:** the field names the [backbone](#term-backbone--backbone) too, as `backbone`. So a changeset names the backbone or a component.
- **Component origin:** where a component came from, which the [manifest](#term-manifest--manifest) records (COR-031 and COR-041).

## TERM-component-origin — component origin

Explained in [VIEW-versions-and-copies](domain-model/040-versions-and-copies.md#component-origin).

**Example:** project-kit's [manifest](#term-manifest--manifest) marks `software-analysis` as `incubated-in-repo`, so [sync](#term-sync--sync) never overwrites the [capability](#term-capability--capability)'s files from the [methodology](#term-methodology--methodology)'s content.

**Distinctions:**

- **The three origins:** `kit-shipped`, `incubated-in-repo` and `externally-sourced`. An entry that names none reads as `kit-shipped` (COR-031 [point](#term-point--point) D2 and COR-041).
- **A rule's origin:** when, by whom and why a [rule](#term-rule--rule) was decided (COR-051 point 5). It shares only the word.
- **Source repository:** where a [component](#term-component--component) is authored. The component is `incubated-in-repo` there, and `externally-sourced` in the projects that pull it (COR-041).

## TERM-connection-point — connection point

Explained in [VIEW-capabilities-areas-and-connection-points](domain-model/030-capabilities-areas-and-connection-points.md#connection-point).

**Example:** `pkit::analysis:revalidation-evidence` is a connection point of the analysis [role](#term-role--role), which a testing [capability](#term-capability--capability) may fill with its results.

**Distinctions:**

- **Data point, process and event:** the three kinds of connection point (COR-053 [point](#term-point--point) 2):
  - a [data point](#term-data-point--data-point) takes data in
  - a process is offered for others to depend on
  - an event signals that a writing command finished
- **Point:** a part of a [decision record](#term-decision-record--decision-record)'s Decision (COR-058 point 1). It shares only the word.
- **Extension point:** COR-053's key in [package metadata](#term-package-metadata--package-metadata) for the connection points a capability defines, beside `extensions` for those it plugs into (COR-053 point 3). A [rule](#term-rule--rule)'s extension point is a part of the rule that an inheriting [rule set](#term-rule-set--rule-set) may fill, and shares only the word (COR-051 point 3).
- **Hook:** a named entry point that an [agent definition](#term-agent-definition--agent-definition) needs and a [skill](#term-skill--skill) or a command provides (COR-013 point 4). It is no connection point.

## TERM-consent — consent

Explained in [VIEW-a-projects-own-files](domain-model/050-a-projects-own-files.md#consent).

**Example:** choosing `pkit upgrade`'s target is the one consent for every [migration](#term-migration--migration) the transition runs (COR-059 [point](#term-point--point) 4).

**Distinctions:**

- **With nobody to ask:** nothing is written, and the default applies (COR-048 point 5).
- **A choice that keeps its own:** such as [merge delivery](#term-merge-delivery--merge-delivery)'s tier that asks, or a [data point](#term-data-point--data-point)'s question. A transition's one consent does not cover it (COR-059 point 4 and COR-061).
- **A person's decision:** an [answer](#term-answer--answer) on an [artefact](#term-artefact--artefact) that the person was shown word for word and accepted before it was written (COR-050 point 3).

## TERM-data-point — data point

Explained in [VIEW-capabilities-areas-and-connection-points](domain-model/030-capabilities-areas-and-connection-points.md#data-point).

**Example:** living-docs accepts `pkit::documentation:readers`, and software-analysis fills it with its actors and their needs.

**Distinctions:**

- **Connection point:** its broader kind. A data point is the kind that takes data in (COR-053 [point](#term-point--point) 2).
- **Combination policy:** how the fillers combine (COR-052 point 3):
  - `single`: one filler answers alone
  - `union`: entries merge by id
  - `additive`: entries merge, and any collision fails
- **Inert filler:** a filler that cannot give a result, such as one out of step with the data point's version. Its failure is never read as an empty result (COR-052 point 6).
- **Question:** a command of the point's definer that asks the person about the point, and records each reply. It runs after an [install](#term-install--install), an upgrade or a [backbone](#term-backbone--backbone) transition (COR-061 points 1 and 2).

## TERM-debt — debt

Explained in [VIEW-artefacts-and-friction](domain-model/070-artefacts-and-friction.md#debt).

**Example:** `pkit friction debt` lists a page stale since the commit that renamed a command it describes, with that commit's author and date.

**Distinctions:**

- **Friction:** a [finding](#term-finding--finding) that a [change](#term-change--change) owes an [answer](#term-answer--answer), which the change gives before it merges. [Friction](#term-friction--friction) nobody answered stays on the [default branch](#term-default-branch--default-branch) as stale debt.
- **Stale and deferred:** stale debt is a change nobody answered, dated from that change. Deferred debt is a deferral, dated from the commit that introduced it (COR-050 [point](#term-point--point) 9).
- **Ledger:** no file lists the debt. Each run derives it from git again (COR-050 point 9).

## TERM-decision-record — decision record

Explained in [VIEW-the-system-and-its-methodology](domain-model/010-the-system-and-its-methodology.md#decision-record).

**Example:** COR-050 is a core record the [methodology](#term-methodology--methodology) ships, and PRJ-002 is one of project-kit's own.

**Distinctions:**

- **Namespace:** COR for core records, PRJ for the [project](#term-project--project)'s, ADR for its architecture and DEC for each [capability](#term-capability--capability)'s (COR-025 and COR-017). Each numbers on its own.
- **Point:** a part of a record's Decision, under an id it keeps for good (COR-058 [point](#term-point--point) 1).
- **Rule:** a statement in a [rule set](#term-rule-set--rule-set) of what must hold of an [artefact](#term-artefact--artefact) (COR-051 point 1). A record chooses and says why, and a [rule](#term-rule--rule)'s origin may cite it.
- **Status:** `proposed`, `accepted` or `superseded`. Work builds only on an accepted record, as the [acceptance gate](#term-acceptance-gate--acceptance-gate) asks.

## TERM-default-branch — default branch

Explained in [VIEW-changes-review-and-releases](domain-model/060-changes-review-and-releases.md#default-branch).

**Example:** project-kit declares none, so its default branch is `main`, which readers resolve as `origin/main` in a clone of its repository.

**Distinctions:**

- **Base:** what a check compares a [change](#term-change--change) with. The default branch is every check's [base](#term-base--base) unless a run names another (COR-054 [point](#term-point--point) 3).
- **Settled state:** what the default branch holds. A [data point](#term-data-point--data-point)'s filler reads it, and never a base named for one run (COR-052 point 6).
- **The local branch:** read only where the [project](#term-project--project) has no remote, and the reader says so (COR-054 point 2).

## TERM-distribution — distribution

Explained in [VIEW-versions-and-copies](domain-model/040-versions-and-copies.md#distribution).

**Example:** project-kit is one distribution, installed from its repository's tags, and a fork that releases from its own repository is another.

**Distinctions:**

- **Release:** one set of [versions](#term-version--version) that a distribution ships. A distribution makes many releases.
- **Source repository:** the repository a distribution is authored and released from.
- **Report target:** the one repository a distribution's reports go to. The distribution sets it, never an adopter (ADR-047 [point](#term-point--point) 3).
- **Externally-sourced component:** a [component](#term-component--component) that a [project](#term-project--project) pulls whole from a repository of the component's own, through the channel its distribution uses (COR-041). It is no distribution.

## TERM-documentation-root — documentation root

Explained in [VIEW-a-projects-own-files](domain-model/050-a-projects-own-files.md#documentation-root).

**Example:** project-kit declares `tech-docs/` as its internal root, so its analysis lives under `tech-docs/analysis/`.

**Distinctions:**

- **Place:** a path declared to hold anchored [artefacts](#term-artefact--artefact) (COR-050 [point](#term-point--point) 1). A root may hold files that no [place](#term-place--place) reads.
- **Space:** living-docs' body of pages for one audience, under a root or in places assigned to it (living-docs DEC-001 point 1).
- **A recorded location:** a location derived from a root is recorded when first used, so changing the root later moves nothing (COR-049 point 5).

## TERM-finding — finding

Explained in [VIEW-changes-review-and-releases](domain-model/060-changes-review-and-releases.md#finding).

**Example:** [validation](#term-validation--validation) fails on a revisit entry that names no target, and only warns of an [anchor](#term-anchor--anchor) on a retired [point](#term-point--point).

**Distinctions:**

- **Friction:** a finding of the [friction](#term-friction--friction) checks, that something an [artefact](#term-artefact--artefact) rests on changed with no [answer](#term-answer--answer) standing for it (COR-050 point 6).
- **Debt:** a finding of the [whole-repository check](#term-whole-repository-check--whole-repository-check), dated from the commit it originates in (COR-050 point 9).
- **Severity:** one of a closed set that every validator shares, of which exactly one fails validation (COR-055 points 4 and 5).
- **A reviewer's finding:** a settled break, a passage for a person or a finding that informs. Only a settled break withholds the [reviewer](#term-reviewer--reviewer)'s approval (COR-057 point 3).

## TERM-friction — friction

Explained in [VIEW-artefacts-and-friction](domain-model/070-artefacts-and-friction.md#friction).

**Example:** a [change](#term-change--change) modifies `src/project_kit/release.py`, and the [change check](#term-change-check--change-check) reports friction on `.pkit/release/README.md` until the page carries an [answer](#term-answer--answer).

**Distinctions:**

- **Debt:** what the [whole-repository check](#term-whole-repository-check--whole-repository-check) reports on the [default branch](#term-default-branch--default-branch). Friction nobody answered is stale [debt](#term-debt--debt), and a deferral is deferred debt (COR-050 [point](#term-point--point) 9).
- **The `friction` block:** the block in an [artefact](#term-artefact--artefact)'s front matter that holds its anchors and answers (COR-050 point 1). It is no [finding](#term-finding--finding).

## TERM-harness — harness

Explained in [VIEW-the-system-and-its-methodology](domain-model/010-the-system-and-its-methodology.md#harness).

**Example:** Claude Code is a harness, and the `claude-code` [adapter](#term-adapter--adapter) serves it.

**Distinctions:**

- **Adapter:** the [component](#term-component--component) that carries the [methodology](#term-methodology--methodology) into one harness.
- **AI agent:** the runtime that works in a harness's session (`ACT-ai-agent`).
- **Harness requirement:** a behaviour the methodology needs of any harness, stated in no harness's own vocabulary (COR-047 [point](#term-point--point) 1).

## TERM-head — head

Explained in [VIEW-changes-review-and-releases](domain-model/060-changes-review-and-releases.md#head).

**Example:** the [change check](#term-change-check--change-check) compares a [pull request](#term-pull-request--pull-request)'s head with where its branch left `main`, and each push gives the pull request a new head.

**Distinctions:**

- **Base:** what a [change](#term-change--change) is compared with, from the commit where its branch left it.
- **Head branch:** the hosting service's name for the branch a pull request merges from.
- **A collection's file head:** the glossary's heading and opening (software-analysis DEC-001 [point](#term-point--point) 1). It shares only the word.

## TERM-install — install

Explained in [VIEW-parts-of-the-system](domain-model/020-parts-of-the-system.md#install).

**Example:** `pkit capabilities install software-analysis` refuses before writing anything when the [backbone](#term-backbone--backbone) lies outside the [capability](#term-capability--capability)'s [range](#term-range--range).

**Distinctions:**

- **First install:** `pkit init`, which installs the backbone and refuses to run again in a [project](#term-project--project) (COR-004).
- **Uninstall:** removes a [component](#term-component--component)'s registration and its copied files, and never the project's own content (COR-010). An incubated capability's files stay where they are (COR-031).
- **Installing the CLI:** puts the [system](#term-system--system)'s command on a machine (PRJ-004). It acts on no project (COR-059 [point](#term-point--point) 5).
- **Version transition:** moves what is installed to another [version](#term-version--version). Install adds what was not there.
- **Registration:** how a project adds a capability it authors itself. Registration copies nothing (COR-031 point D3).

## TERM-manifest — manifest

Explained in [VIEW-versions-and-copies](domain-model/040-versions-and-copies.md#manifest).

**Example:** project-kit's `.pkit/manifest.yaml` records [backbone](#term-backbone--backbone) 1.149.0, and lists each installed [component](#term-component--component) with the path of that component's own manifest.

**Distinctions:**

- **The backbone's:** `.pkit/manifest.yaml`. It holds the backbone's target and completion. It lists each component with its origin and the path of the component's own (COR-010 and ADR-065 [point](#term-point--point) 2).
- **A shipped component's:** under the component's `project/` folder, with its [recorded version](#term-recorded-version--recorded-version) and the files its [install](#term-install--install) skipped (COR-059 point 7 and ADR-065 point 2).
- **Package metadata:** what a component declares about itself as it ships. A manifest is what the [project](#term-project--project) recorded when it installed the component.
- **Version pin:** a directive naming the [release](#term-release--release) whose [system](#term-system--system) runs the project's commands (ADR-049 point 1). A manifest records what content the project holds.
- **The methodology's path lists:** COR-001 and COR-002 call the lists of synced and seeded paths manifests too. They are lists the [methodology](#term-methodology--methodology) keeps, not a project's file.

## TERM-merge-delivery — merge delivery

Explained in [VIEW-a-projects-own-files](domain-model/050-a-projects-own-files.md#merge-delivery).

**Example:** [sync](#term-sync--sync) adds the [methodology](#term-methodology--methodology)'s missing entries to `.claude/settings.json`, and every entry project-kit added there stays.

**Distinctions:**

- **Merge:** landing a [change](#term-change--change) on the [default branch](#term-default-branch--default-branch). The analysis writes merge delivery in full for this operation.
- **The tier that asks:** entries put to a person once, at [install](#term-install--install), by the merge command or in a [version transition](#term-version-transition--version-transition). Sync runs only the tier that asks nothing (COR-059 [point](#term-point--point) 2).
- **Seeding:** creates a missing declared seed path from its template, never over a file that exists (COR-059 point 8). Merge delivery revisits its file on each run.

## TERM-methodology — methodology

Explained in [VIEW-the-system-and-its-methodology](domain-model/010-the-system-and-its-methodology.md#methodology).

**Example:** the developer records a decision beside the methodology's, and builds only on accepted records, as the methodology's [acceptance gate](#term-acceptance-gate--acceptance-gate) asks.

**Distinctions:**

- **The system:** the software under discussion, which you put on a machine, run and extend. A sentence that means the software, such as one about installing it, says *the [system](#term-system--system)* (PR #1374). It is a term of its own, whose *Distinctions* refer back here.
- **The methodology maintainer:** an actor, "whoever maintains a [distribution](#term-distribution--distribution) of the methodology" (`ACT-methodology-maintainer`). The actor also works on parts of the system, such as the [backbone](#term-backbone--backbone) and its releases. So its name, which the maintainer kept (PR #1374), uses the word more widely than this term.
- **A capability's discipline:** what one [capability](#term-capability--capability) packages, for a [project](#term-project--project) to [install](#term-install--install) or leave out (COR-017). A capability the system ships carries one part of the methodology, never the whole. A capability a project or its organisation writes is their own (COR-031 and COR-041).

## TERM-migration — migration

Explained in [VIEW-versions-and-copies](domain-model/040-versions-and-copies.md#migration).

**Example:** project-management renamed its [reviewer](#term-reviewer--reviewer)'s [agent definition](#term-agent-definition--agent-definition) from `reviewer` to `pm-reviewer`. So the [capability](#term-capability--capability)'s migration `0.55.0/001-pm-reviewer-agent-rename.sh` makes the same rename in each [project](#term-project--project)'s own settings, which [sync](#term-sync--sync) never touches.

**Distinctions:**

- **Sync:** the operation that rewrites a project's [synced copies](#term-synced-copy--synced-copy) at its [recorded versions](#term-recorded-version--recorded-version). It runs no migration. A migration changes what sync cannot derive, such as a project's own settings (COR-010).
- **The migration check:** `pkit migrations check-diff`, which finds the renames and removals of a [change](#term-change--change) that no migration covers. It runs no migration.

## TERM-operational-rule — operational rule

Explained in [VIEW-the-system-and-its-methodology](domain-model/010-the-system-and-its-methodology.md#operational-rule).

**Example:** core rule 8 asks an agent to pause before a destructive operation, and [project](#term-project--project) rule 4 asks for signed commits in project-kit.

**Distinctions:**

- **Rule:** a statement in a [rule set](#term-rule-set--rule-set), with an id, an origin and a status (COR-051). An operational rule shares only the word.
- **Core rule and project rule:** the analysis's names for an operational rule of the [methodology](#term-methodology--methodology)'s file and of the project's, cited by number, as in *core rule 2*. Neither is a [rule](#term-rule--rule) of a rule set.
- **Core or project:** the methodology's file holds what fits any project, and the project's file holds what fits only that project (COR-014).

## TERM-package-metadata — package metadata

Explained in [VIEW-artefacts-and-friction](domain-model/070-artefacts-and-friction.md#package-metadata).

**Example:** `software-analysis`'s `package.yaml` declares the glossary as a [place](#term-place--place) whose entries take the type `software-analysis:term`.

**Distinctions:**

- **Manifest:** the [project](#term-project--project)'s record of what it installed, at which [version](#term-version--version). COR-017 uses that word for the package metadata too, and the analysis keeps it for the project's record.
- **Plan:** a dry run that reads a [capability](#term-capability--capability)'s [connection points](#term-connection-point--connection-point) from its package metadata, before the capability is installed (COR-053 [point](#term-point--point) 8).

## TERM-place — place

Explained in [VIEW-artefacts-and-friction](domain-model/070-artefacts-and-friction.md#place).

**Example:** project-kit lists `.pkit/cli/README.md` in `friction.places`, so the [backbone](#term-backbone--backbone) reads that page's anchors.

**Distinctions:**

- **Documentation root:** where a [project](#term-project--project) keeps its documents, for users or for itself. A place may lie inside a root, and a root may hold files no place reads.
- **Synced copy:** a file that [propagation](#term-propagation--propagation) writes into the project, such as a core record. A folder of [synced copies](#term-synced-copy--synced-copy) is never a place, or each [sync](#term-sync--sync) would read as [friction](#term-friction--friction) (COR-050 [point](#term-point--point) 14).
- **Held folder:** a folder a [component](#term-component--component) declares for its held documents. No place reads a file in it as an [artefact](#term-artefact--artefact) (COR-050 point 1).

## TERM-point — point

Explained in [VIEW-the-system-and-its-methodology](domain-model/010-the-system-and-its-methodology.md#point).

**Example:** COR-050 point 3 says who decides an [answer](#term-answer--answer), and an [artefact](#term-artefact--artefact) anchors it as `COR-050#3`.

**Distinctions:**

- **Retired point:** one that no other point continues. Its id stays in the record's front matter, with a stub where it stood (COR-058 point 4).
- **A record in list form:** a record whose points are still numbered items. Their numbers may move, so no [anchor](#term-anchor--anchor) names one (COR-058 point 9).
- **Revalidation point and deferral point:** commits that the [friction](#term-friction--friction) checks measure from (COR-050 points 3 and 4). They share only the word.
- **Connection point:** a [component](#term-component--component)'s declared interface under a [role](#term-role--role) (COR-053 point 2). It shares only the word.

## TERM-project — project

Explained in [VIEW-parts-of-the-system](domain-model/020-parts-of-the-system.md#project).

**Example:** an adopter's repository becomes a project when `pkit init` installs the [system](#term-system--system) there, and project-kit's own repository is a project too.

**Distinctions:**

- **Adopter:** the person who adopts the [methodology](#term-methodology--methodology) for a project and keeps its setup (`ACT-adopter`). A project is the repository, never the person.
- **Source repository:** where a [distribution](#term-distribution--distribution) or a [component](#term-component--component) is authored. project-kit's own repository is a [source repository](#term-source-repository--source-repository) and a project at once, so the methodology's files there are originals, not [synced copies](#term-synced-copy--synced-copy).
- **Project-owned content:** what a project writes and keeps in itself. Each file a project tracks has one owner, the methodology or the project, never both (the no-shared-files invariant).
- **The `project/` folder:** an [area](#term-area--area)'s half for a project's own content (COR-003). It is part of a project, and no project of its own.

## TERM-project-owned-content — project-owned content

Explained in [VIEW-a-projects-own-files](domain-model/050-a-projects-own-files.md#project-owned-content).

**Example:** project-kit's records in `.pkit/decisions/project/`, its [backbone configuration](#term-backbone-configuration--backbone-configuration) and its root `CLAUDE.md` are project-owned content.

**Distinctions:**

- **Project:** the repository that holds this content. The definition says *installed repository*, since a definition holds no word of its term's name.
- **Synced copy:** the [methodology](#term-methodology--methodology)'s file in a [project](#term-project--project), which [propagation](#term-propagation--propagation) rewrites. A project adds its own content beside a [synced copy](#term-synced-copy--synced-copy), and never edits one (COR-003).
- **Writers a record names:** among them these, each writing with the [consent](#term-consent--consent) its record sets (COR-001):
  - [seeding](#term-seeding--seeding) and [merge delivery](#term-merge-delivery--merge-delivery)
  - a [migration](#term-migration--migration), within what the records owning the written content allow
  - a [capability](#term-capability--capability)'s [install](#term-install--install), of the [rule set](#term-rule-set--rule-set) the capability declares
  - the configuration commands (COR-048 [point](#term-point--point) 5)
- **Extension:** COR-001's name for this content. COR-053's `extensions` and a [rule](#term-rule--rule)'s extension point are other things (COR-053 point 3 and COR-051 point 3).
- **Suspension:** project-owned content that its consumer reads instead of a synced copy of the same name. The record governing that kind of file must allow it (COR-001).

## TERM-propagation — propagation

Explained in [VIEW-versions-and-copies](domain-model/040-versions-and-copies.md#propagation).

**Example:** `pkit capabilities install` runs propagation for one [capability](#term-capability--capability), copying its subtree from the bundle at the [backbone](#term-backbone--backbone) the [project](#term-project--project) records (ADR-065 [point](#term-point--point) 1).

**Distinctions:**

- **Synced copy:** a file that propagation writes into a project.
- **Sync:** runs propagation at the [recorded versions](#term-recorded-version--recorded-version). [Sync](#term-sync--sync) also regenerates the deployed copies, and runs [merge delivery](#term-merge-delivery--merge-delivery)'s tier that asks nothing (COR-059 point 2).
- **Seeding:** creates a missing project-owned file once, and never writes over one that exists (COR-059 point 8).

## TERM-pull-request — pull request

Explained in [VIEW-changes-review-and-releases](domain-model/060-changes-review-and-releases.md#pull-request).

**Example:** the pull request that landed UC-008 targeted `main`, and its conventional title became the squash commit's subject.

**Distinctions:**

- **Change:** the unit of work a pull request carries. Where the [project](#term-project--project) allows it, a [change](#term-change--change) may land as a direct commit instead (COR-009 [point](#term-point--point) 5).
- **Target:** the branch a pull request merges into, which CI names as the checks' [base](#term-base--base).
- **Release pull request:** the pull request that carries one [release step](#term-release-step--release-step)'s writes (PRJ-002 D3).

## TERM-range — range

Explained in [VIEW-capabilities-areas-and-connection-points](domain-model/030-capabilities-areas-and-connection-points.md#range).

**Example:** the `software-analysis` [capability](#term-capability--capability) declares `requires_backbone: ">=1.149.0,<2.0.0"`, a range on the [backbone](#term-backbone--backbone) whose floor is 1.149.0.

**Distinctions:**

- **Floor:** the lowest [version](#term-version--version) a range admits, its `>=X.Y.Z`. At a [release step](#term-release-step--release-step), a floor rises only where a [changeset](#term-changeset--changeset) declares that the [component](#term-component--component) needs a newer version (PRJ-002 D4).
- **Upper bound:** the version a range stops below, its `<A.B.C`. A release step widens an upper bound on the backbone with no declaration. It widens an upper bound on another capability only on a changeset's declaration (PRJ-002 D4).
- **A component's version:** the one number the component carries in its `package.yaml`, as the backbone carries its own in `.pkit/VERSION`. A range names versions of what the component depends on (COR-010 and COR-030).
- **Harness version bound:** the [harness](#term-harness--harness) versions that an [adapter](#term-adapter--adapter)'s support declaration holds for. It is never widened automatically, only by an author who tested the claim (COR-047 [point](#term-point--point) 2).

## TERM-recorded-version — recorded version

Explained in [VIEW-versions-and-copies](domain-model/040-versions-and-copies.md#recorded-version).

**Example:** an adopter's [manifest](#term-manifest--manifest) records [backbone](#term-backbone--backbone) 1.149.0, so `pkit sync` there writes the content of that [release](#term-release--release) and moves no [version](#term-version--version).

**Distinctions:**

- **Version pin:** a directive the [project](#term-project--project) owns, naming the release whose [system](#term-system--system) runs its commands (ADR-049 [point](#term-point--point) 1). A recorded version records the content held.
- **Where it is kept** (ADR-065 point 2):
  - the backbone's and a shipped [component](#term-component--component)'s, in their manifests
  - an incubated [capability](#term-capability--capability)'s, in its [package metadata](#term-package-metadata--package-metadata), where the project moves it by editing it (COR-059 point 1)
  - an externally-sourced component's, as its pin, COR-041's word for the ref the component is pulled at
- **Completion:** the state a transition of the backbone records last. While a transition is incomplete, the backbone's recorded version names its target (COR-059 points 1 and 6).

## TERM-release — release

Explained in [VIEW-versions-and-copies](domain-model/040-versions-and-copies.md#release).

**Example:** the release of 24 August 2026 holds [backbone](#term-backbone--backbone) 1.149.0 and, among its [components](#term-component--component), project-management 0.54.0. Its release commit carries the tag `v1.149.0`.

**Distinctions:**

- **Release step:** the procedure that makes a release from the pending [changesets](#term-changeset--changeset). To release a component is to run the [release step](#term-release-step--release-step) for that component's changesets.
- **Changeset:** a [change](#term-change--change)'s declaration for the next release. The release step consumes every changeset waiting for it (PRJ-002 D1 and D3).
- **A release step that moves no backbone:** writes new [versions](#term-version--version) of components and makes no release of its own. Those versions reach a CLI installed from a tag with the next release (PRJ-004).
- **A component's release:** PRJ-002's and PRJ-004's name for one new version of one component (PRJ-002 D4). The analysis calls it the component's new version.
- **An externally-sourced component's version:** written in the component's own [source repository](#term-source-repository--source-repository), and reached by a [project](#term-project--project)'s transition of that component (COR-041).
- **Release pull request:** the [pull request](#term-pull-request--pull-request) that carries one release step's writes, on a `release/` branch under a `chore(release):` title. It closes no issue, so `pkit release merge` lands it.
- **Release tag:** the annotated tag `v<version>` on the release commit. Each release gets one, and a release step that moves only components gets none (PRJ-004).
- **GitHub release:** the page the hosting service shows for a tag. Its notes are the version's changelog section, and it carries no file (PRJ-004).

## TERM-release-step — release step

Explained in [VIEW-changes-review-and-releases](domain-model/060-changes-review-and-releases.md#release-step).

**Example:** `pkit release plan` previews what the next release step writes, and `pkit release apply` writes it on a `release/` branch.

**Distinctions:**

- **Release:** the set of [versions](#term-version--version) a release step makes when it moves the [backbone](#term-backbone--backbone). A release step that moves only [components](#term-component--component) makes none of its own (PRJ-004).
- **Changeset:** what a branch writes instead of a version number, declaring its [change](#term-change--change) for the release step (PRJ-002 D1).
- **Release pull request:** the [pull request](#term-pull-request--pull-request) that carries one release step's writes onto the [default branch](#term-default-branch--default-branch) (PRJ-002 D3).

## TERM-report — report

Explained in [VIEW-changes-review-and-releases](domain-model/060-changes-review-and-releases.md#report).

**Example:** an adopter's `pkit report bug` files an issue titled `[Bug] …` on project-kit's repository, with the adopter's [versions](#term-version--version) attached.

**Distinctions:**

- **Report target:** the one repository a [distribution](#term-distribution--distribution)'s reports go to, project-kit's own for project-kit. An adopter cannot name another (ADR-047 [point](#term-point--point) 3).
- **Tracked fix:** an issue the maintainer lists under a report's `## Tracked by` heading. One issue may fix several reports (PRJ-008).
- **Reported note:** a scratchpad note attached to a report. Once the report is posted, the note moves to `reported/` (COR-043 point 3).
- **The whole-repository report:** what the [whole-repository check](#term-whole-repository-check--whole-repository-check) publishes for the [default branch](#term-default-branch--default-branch), such as project-kit's tracking issue. It is no report in this sense.

## TERM-reviewer — reviewer

Explained in [VIEW-changes-review-and-releases](domain-model/060-changes-review-and-releases.md#reviewer).

**Example:** the rule-set reviewer judges a [change](#term-change--change) against the rules that bind on what the change alters, and withholds its approval for a settled break.

**Distinctions:**

- **The reviewer stack:** the critic and the architect advise on a draft. The `methodology-reviewer`, the `convention-compliance-reviewer` and the `rule-set-reviewer` judge an [artefact](#term-artefact--artefact) or a diff. The [backbone](#term-backbone--backbone) ships all five (COR-024 and COR-057).
- **Verdict:** a reviewer agent's judgement of a [pull request](#term-pull-request--pull-request), posted where a merge gate reads it (project-management DEC-028).
- **The answers' reviewer:** the reviewer the [project](#term-project--project) chooses to check the answers an agent wrote for its own change (COR-050 [point](#term-point--point) 3).
- **Merge authoriser:** the person who authorises a merge (`ACT-merge-authoriser`). A reviewer's approval is never that authorisation (project-management DEC-055 point 3).

## TERM-role — role

Explained in [VIEW-capabilities-areas-and-connection-points](domain-model/030-capabilities-areas-and-connection-points.md#role).

**Example:** living-docs provides the documentation role, so software-analysis contributes its readers to that role's [data point](#term-data-point--data-point) for readers, without naming living-docs.

**Distinctions:**

- **Actor:** a person, or other software such as a CI pipeline, that uses the [system](#term-system--system). software-analysis DEC-001 [point](#term-point--point) 1 calls an actor a named role.
- **A role in a record:** the part a record names instead of whatever plays it today (COR-046 point 1). It is a part of the design, not a [capability](#term-capability--capability)'s role.
- **An artefact's role:** the kind of content that one shape of document carries, such as a [skill](#term-skill--skill)'s procedure (COR-006).
- **Agent definition:** what COR-006 calls a persistent role with boundaries. The analysis calls it an [agent definition](#term-agent-definition--agent-definition).
- **Provider:** the installed capability that supplies a role's [connection points](#term-connection-point--connection-point). Where two installed capabilities provide one role, the [project](#term-project--project) selects one (COR-053 points 1 and 7).

## TERM-rule — rule

Explained in [VIEW-the-system-and-its-methodology](domain-model/010-the-system-and-its-methodology.md#rule).

**Example:** RS-WRITE-005 keeps every sentence of the analysis to at most 25 words, and binds on the analysis through `ANA`, which inherits `WRITE`.

**Distinctions:**

- **Rule set:** the collection file that holds rules, each an [artefact](#term-artefact--artefact) of its own (COR-051 [point](#term-point--point) 2).
- **Operational rule:** an instruction every AI agent session loads, with no id, origin or status. COR-051 point 1 does not govern it.
- **Decision record:** chooses among alternatives and says why. A rule says what must hold, and its origin may cite the record (COR-051 point 5).
- **Proposed rule:** one that binds nothing until it is accepted. An accepted rule binds only on the artefacts that a [rule set](#term-rule-set--rule-set) of the [project](#term-project--project)'s own reaches (COR-051 points 4 and 7).

## TERM-rule-set — rule set

Explained in [VIEW-artefacts-and-friction](domain-model/070-artefacts-and-friction.md#rule-set).

**Example:** `ANA` is project-kit's rule set for its analysis. Its scope selects the analysis by type, and it inherits `WRITE@2` and `software-analysis:SAN@1`.

**Distinctions:**

- **Rule:** one entry of a rule set, an [artefact](#term-artefact--artefact) of its own (COR-051 [point](#term-point--point) 2).
- **Method rule set:** one that the [backbone](#term-backbone--backbone) or a [component](#term-component--component) ships. It takes no scope, so its rules bind only through a set of the [project](#term-project--project)'s own that inherits it (COR-051 points 6 and 7).
- **Pin:** the major number an inheriting set names for each set it inherits, as in `WRITE@2`. No [rule](#term-rule--rule) binds through a pin behind its set until the project reviews the new major (COR-051 point 7).
- **Version pin:** the [release](#term-release--release) a project's commands run at (ADR-049 point 1). It is no rule set's pin.

## TERM-seeding — seeding

Explained in [VIEW-a-projects-own-files](domain-model/050-a-projects-own-files.md#seeding).

**Example:** a [project](#term-project--project) that deleted its agents overlay gets it back from the template at its next `pkit upgrade` (COR-059 [point](#term-point--point) 8).

**Distinctions:**

- **The seeded file:** [project-owned content](#term-project-owned-content--project-owned-content) from the moment it is written (COR-001).
- **Merge delivery:** revisits its file on every run to add entries. Seeding never writes over a file that exists (COR-059 point 8).
- **Sync:** creates no seed path (COR-059 point 8).
- **Stamp:** writes a new file when a person or an agent asks for one.

## TERM-skill — skill

Explained in [VIEW-parts-of-the-system](domain-model/020-parts-of-the-system.md#skill).

**Example:** the `analysis-author` skill walks an AI agent through a term's slug and anchors, then runs the [stamp](#term-stamp--stamp) `pkit analysis new term`.

**Distinctions:**

- **Agent definition:** a remit with boundaries that a [harness](#term-harness--harness) delegates to. A skill is a procedure, which whichever AI agent does the task loads (COR-006).
- **Stamp:** the command an authoring skill pairs with. The skill carries the disciplines, and the stamp writes the file (COR-005).
- **Composite skill:** one skill whose folder holds a procedure for each operation of a family, such as `analysis-author` (COR-020).

## TERM-source-repository — source repository

Explained in [VIEW-versions-and-copies](domain-model/040-versions-and-copies.md#source-repository).

**Example:** project-kit's repository is the source repository of its [distribution](#term-distribution--distribution), so its `.pkit/decisions/core/` holds the core records as they are authored, and may be a [place](#term-place--place).

**Distinctions:**

- **Synced copy:** a file that [sync](#term-sync--sync) writes into a [project](#term-project--project) from what a source repository authored. One tree is source in its own repository, and its files are [synced copies](#term-synced-copy--synced-copy) in every other (COR-050 [point](#term-point--point) 14).
- **Project:** a source repository that installs what it builds is a project too, as project-kit's is.
- **Component origin:** a [component](#term-component--component) authored in a repository is `incubated-in-repo` there, and `externally-sourced` in the projects that pull it (COR-041).

## TERM-stamp — stamp

Explained in [VIEW-parts-of-the-system](domain-model/020-parts-of-the-system.md#stamp).

**Example:** `pkit analysis new term` is the stamp behind each entry of this glossary, and the `analysis-author` [skill](#term-skill--skill) pairs with it.

**Distinctions:**

- **Skill:** the procedure a stamp pairs with. The skill chooses the slug and fills the body, and the stamp writes what it can compute (COR-005).
- **Provenance stamp:** project-management's record of the [versions](#term-version--version) an issue or a [pull request](#term-pull-request--pull-request) was filed under (project-management DEC-041). It is no command.
- **Seeding:** creates a missing declared seed path from its template (COR-059 [point](#term-point--point) 8). A stamp writes a new file when a person or an AI agent asks for one.

## TERM-surface-change — surface change

Explained in [VIEW-changes-review-and-releases](domain-model/060-changes-review-and-releases.md#surface-change).

**Example:** a new subcommand of `pkit` is a surface change, so its [pull request](#term-pull-request--pull-request) declares it in a [changeset](#term-changeset--changeset) (PRJ-002 D1).

**Distinctions:**

- **A component's surface paths:** the paths the changeset guard reads as a [component](#term-component--component)'s surface. An edit to one only suggests a surface change, and a person judges it (PRJ-002 D2).
- **Declared surface:** the paths a [project](#term-project--project) or a component says its descriptions ought to cover. Those no [artefact](#term-artefact--artefact) anchors are reported as uncovered (COR-050 [point](#term-point--point) 8).

## TERM-sync — sync

Explained in [VIEW-versions-and-copies](domain-model/040-versions-and-copies.md#sync).

**Example:** after a fresh clone, `pkit sync` deploys the [skills](#term-skill--skill) and [agent definitions](#term-agent-definition--agent-definition) again, and rewrites the core records at the [recorded version](#term-recorded-version--recorded-version).

**Distinctions:**

- **Version transition:** moves the recorded versions and runs [migrations](#term-migration--migration). Sync does neither (COR-059 points 2 and 3).
- **Sync's guard:** under a CLI at another [version](#term-version--version) than the [project](#term-project--project) records, or over an incomplete transition, sync stops and writes nothing (COR-059 [point](#term-point--point) 9).
- **Reconciling against a source:** what COR-031 and COR-041 call the copying that sync and a [version transition](#term-version-transition--version-transition) both run (COR-059 point 2).
- **Seeding:** sync creates no seed path (COR-059 point 8).

## TERM-synced-copy — synced copy

Explained in [VIEW-versions-and-copies](domain-model/040-versions-and-copies.md#synced-copy).

**Example:** `.pkit/decisions/core/COR-050-anchors-and-friction.md` is a synced copy in an adopter's [project](#term-project--project), so the next [sync](#term-sync--sync) overwrites any edit made there.

**Distinctions:**

- **Project-owned content:** what a project writes and keeps. Sync writes a project-owned file only through [merge delivery](#term-merge-delivery--merge-delivery) (COR-059 [point](#term-point--point) 2).
- **Source repository:** where the same file is authored. There it is no synced copy (COR-050 point 14).
- **Place:** a folder of synced copies is never one, or each sync would read as [friction](#term-friction--friction) in the project's history (COR-050 point 14).
- **Deployed copy:** what an [adapter](#term-adapter--adapter) regenerates for its [harness](#term-harness--harness) from a [skill](#term-skill--skill) or an [agent definition](#term-agent-definition--agent-definition), such as a link under `.claude/skills/`. Neither the project nor the [methodology](#term-methodology--methodology) owns it (COR-003).

## TERM-system — system

Explained in [VIEW-the-system-and-its-methodology](domain-model/010-the-system-and-its-methodology.md#system).

**Example:** the system ends a [pull request](#term-pull-request--pull-request)'s landing `merged`, naming the [head](#term-head--head) the pull request merged at (`pkit pull-request land`).

**Distinctions:**

- **pkit:** the product's name, kept in prose and in commands. The analysis says *the system* for the same software (PR #1374).
- **A system:** other software, such as the hosting service or the [harness](#term-harness--harness). The analysis names it for what it is, never a system (PR #1345, question 12).
- **A platform:** in COR-009, the hosting service a [project](#term-project--project)'s remote lives on. It is other software, never the system.
- **The methodology:** the body of [decision records](#term-decision-record--decision-record), rules, [operational rules](#term-operational-rule--operational-rule) and conventions the system ships and enforces. It is a term of its own, whose *Distinctions* refer back here.

## TERM-validation — validation

Explained in [VIEW-a-projects-own-files](domain-model/050-a-projects-own-files.md#validation).

**Example:** `pkit validate` fails on a dangling deferral, and warns that project-kit's user root, `docs/`, does not exist yet.

**Distinctions:**

- **Change check:** compares a [change](#term-change--change) with its [base](#term-base--base). Validation reads the working tree, and takes no base (COR-055 [point](#term-point--point) 2).
- **Whole-repository check:** reports [debt](#term-debt--debt) on the [default branch](#term-default-branch--default-branch), and never fails (COR-055 point 1).
- **Validator:** a command a [component](#term-component--component) registers, whose [findings](#term-finding--finding) validation reads. A validator that gives no result yields a failing finding (COR-055 points 3 and 6).

## TERM-version — version

Explained in [VIEW-parts-of-the-system](domain-model/020-parts-of-the-system.md#version).

**Example:** [backbone](#term-backbone--backbone) 1.149.0 and project-management 0.54.0 are versions, and a `minor` [changeset](#term-changeset--changeset) has the next [release step](#term-release-step--release-step) move the backbone to 1.150.0.

**Distinctions:**

- **A rule set's version:** its own, apart from its [component](#term-component--component)'s. An inheriting set pins its major (COR-051 [point](#term-point--point) 7).
- **A connection point's version:** an integer that rises only on an edit that breaks its counterparts (COR-053 point 5).
- **A schema version:** the integer a schema and the data it checks each carry (COR-052 point 5 and COR-023).
- **Recorded version:** the number or ref a [project](#term-project--project) keeps for what it installed. An externally-sourced component's ref is no version in the sense of this term.

## TERM-version-pin — version pin

Explained in [VIEW-a-projects-own-files](domain-model/050-a-projects-own-files.md#version-pin).

**Example:** `pkit upgrade` writes `.pkit/version-pin` at the [release](#term-release--release) it brought the [project](#term-project--project) to, so each later command there runs at that release.

**Distinctions:**

- **Recorded version:** a record of the content a project holds. A version pin is a directive the project owns (ADR-049 [point](#term-point--point) 1).
- **A rule set's pin:** the major number an inheriting [rule set](#term-rule-set--rule-set) names for a set it inherits (COR-051 point 7). The analysis writes *version pin* in full for this term.
- **An external source's pin:** the ref an externally-sourced [component](#term-component--component) is pulled at, which is that component's [recorded version](#term-recorded-version--recorded-version) (COR-041).
- **The installed CLI:** the command on the machine. A pinned project runs the installed CLI only where its pin cannot be fetched, and is warned (ADR-064).
- **The source repository:** never pinned (ADR-064 point 3).

## TERM-version-transition — version transition

Explained in [VIEW-versions-and-copies](domain-model/040-versions-and-copies.md#version-transition).

**Example:** `pkit upgrade` runs a transition of the [backbone](#term-backbone--backbone), which moves project-management with it to the [version](#term-version--version) the target [release](#term-release--release) ships.

**Distinctions:**

- **Upgrade:** the command, and a transition to a later release. A transition of the backbone only moves forward (COR-059 [point](#term-point--point) 9).
- **Sync:** keeps a [project](#term-project--project) at its [recorded versions](#term-recorded-version--recorded-version), and moves none.
- **Updating the CLI:** acts on no project, so a command may first update the CLI that runs it (COR-059 point 5).
- **A transition of one component:** moves that [component](#term-component--component) to the version the project's release ships, without moving the backbone (COR-059 point 3).

## TERM-whole-repository-check — whole-repository check

Explained in [VIEW-artefacts-and-friction](domain-model/070-artefacts-and-friction.md#whole-repository-check).

**Example:** `pkit friction check --all` on the [default branch](#term-default-branch--default-branch) lists a page stale since the commit that renamed a command the page describes.

**Distinctions:**

- **Change check:** compares one [change](#term-change--change) with its [base](#term-base--base), and fails in enforcing mode (COR-050 [point](#term-point--point) 12).
- **Debt:** what the whole-repository check reports, derived from git on each run (COR-050 point 9).
- **Tool-written status:** the `last-check` that an after-merge job writes from the check's result. The checks never read it for [friction](#term-friction--friction) (COR-050 point 10).
