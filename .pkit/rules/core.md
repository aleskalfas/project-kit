*Operational rules shipped by the methodology core, kept as the backbone's loaded rule set `OPS` (COR-068). The loaded file is generated from `.pkit/rule-sets/ops.md`, where the set is authored, by `pkit rule-sets generate`; a project that receives them by sync edits neither (core rule 1). A rule cites the record or issue its reason lives in, and where it cites neither, its origin in the set holds the reason: read it when the why is not obvious, and keep the rule meanwhile. Every layer's rules bind at once: core's, each installed capability's and the project's. A capability's rules and a project's add to core's and never loosen them, and where a rule cannot be kept with one of a layer above it, the upper layer's binds (COR-070).*

## Hard rules

Violating any of these breaks the methodology's invariants. Treat them as gates, not guidelines.

### 1. The no-shared-files invariant (RS-OPS-001)

**The no-shared-files invariant.** Every file has exactly one owner, the methodology core or the project. Never edit a core-owned file, which sync overwrites; extend core content with sibling files in the matching `project/` directory, or in the file the adapter merges into (COR-001; the decisions README, "The no-shared-files invariant").

### 2. The acceptance gate (RS-OPS-002)

**The acceptance gate.** Act only on accepted decisions and rules: a proposed one binds nothing, so no code, document or record may rest on it. A person accepts a proposal within the change that proposes it, and an agent writes `accepted` only once that person has. Until then the work resting on it waits and the change does not land, and a change built on it lands no earlier than the change that proposes it. Before the change is authorised to reach the default branch, the person who authorises it sees each record and rule the change makes accepted, shown by the component that carries out merges or, without one, by the change's author; an edit made after the acceptance is accepted only through that list (COR-066 points 1 and 3).

### 3. Author core-shipped artifacts through the paired skill or `pkit new` (RS-OPS-003)

**Author core-shipped artifacts (decisions, adapters, migrations, areas, scratchpad notes, agents, capabilities) through the paired skill or `pkit new <kind>`, and never hand-stamp the file.** The command stamps numbering, front matter and layout, and the skill carries the disciplines (COR-005, "Skill / command pairing"; the CLI README, "Authoring commands").

### 4. PRJ records live in `.pkit/decisions/project/` (RS-OPS-004)

**PRJ records live in `.pkit/decisions/project/`; never edit `.pkit/decisions/core/`,** whose records sync refreshes (COR-001; the decisions README, "Two namespaces, two prefixes").

### 5. Migrations are idempotent and safe over any state (RS-OPS-005)

**Migrations are idempotent, and a backbone migration is safe over any state.** A migration you write must detect state already migrated and exit cleanly. A backbone migration must also act only on a positive sign that its change is needed, and never delete by a path's name or position alone. A missing default it adds counts as such a sign, so if it adds one, say in the release's notes that a replay may restore a default the project removed (COR-010; the lifecycle README, "Script contract").

### 6. Settings-file changes go through the merge primitive (RS-OPS-006)

**Settings-file changes go through the merge primitive.** Change a fixed-path config file, such as `.claude/settings.json` or `.gitignore`, only on its project-additions side, never directly to add core-shipped content; the adapter merges the baseline in (COR-002).

### 7. Surface changes ship a migration in the same change-set (RS-OPS-007)

**Surface changes ship a migration in the same change-set.** A change that breaks against an installed project's state (a rename or removal in a tree the methodology ships, backbone, adapter or capability; a `schema_version` bump; a breaking CLI signature; a capability subtree restructure) carries an idempotent migration at the affected tier in the same commit or pull request. Before committing, check your diff for these triggers, and verify coverage with `pkit migrations check-diff --include-working-tree` (COR-010, "Migrations are mandatory on adopter-breaking surface changes").

## Tool hygiene

### 8. Pause and confirm before destructive operations (RS-OPS-008)

**Pause and confirm before destructive operations,** such as `git reset --hard`, `git push --force`, `rm -rf`, deleting files outside `project/`, dropping tables or killing processes. Each needs the user's explicit confirmation, even where the task seemed to authorise it, and a confirmation covers that operation alone.

### 9. Conventional commits, one logical unit each (RS-OPS-009)

**Use conventional commits and keep one logical unit per commit.** The branch-naming convention, `<type>/<issue-number>-<slug>`, is COR-008's: see its "Operational reference" section for the recommended type list, the convention and its examples.

### 10. Surface changes bump the version of the affected component (RS-OPS-010)

**Surface changes bump the version of the affected component.** A surface change is one an adopter could observe, depend on or break against, not a documentation refinement or internal refactor; each project records its bump policy as a PRJ record, and each component's version follows it alike (COR-010).

### 11. Validate before assuming state (RS-OPS-011)

**Validate before assuming state.** Read how the methodology is wired here from `pkit status`, not from a prior session; the file system is the source of truth.

### 12. Skills and agents are deployed by the adapter (RS-OPS-012)

**Skills and agents are deployed by the adapter, not hand-symlinked.** The adapter's deploy primitives (e.g. `deploy-skills.sh` and `deploy-agents.sh` for Claude Code, the second per COR-013) deploy canonical content from `.pkit/skills/` and `.pkit/agents/` into the harness's expected location: skills as symlinks, agents as copies with their overlay placeholders resolved. Editing the deployed symlinks or copies instead of the canonical core-side file violates the no-shared-files invariant.

### 13. An included file has no H1 (RS-OPS-013)

**A file meant for an `@<path>` include has no H1** and starts with prose or H2 sections, since the host owns the H1; place the include after the host's intro paragraph, not at line 1 (Claude Code; other harnesses' include rules are in their adapter READMEs).

### 14. Don't escalate past the permission model (RS-OPS-014)

**Don't escalate past the permission model for commands it already permits.** Run an allowlisted command, such as version control, the issue tracker or the methodology's CLI, as it is inside the sandbox, and keep a sandbox-escape or escalation flag for the rare command that cannot run within the model, since each one forces a confirmation by hand (project-kit#71; the permission model, COR-028; `pkit permissions sandbox toolkit list` shows what the sandbox permits).

### 15. Work with the permission layer, not around it (RS-OPS-015)

**Work with the permission layer, not around it.** Issue the narrowest action it can vet: one simple command rather than a compound, and the harness's own read, search and write tools for inspection. Extract a recurring or non-trivial diagnostic into a committed command (COR-007), and never compose a command to slip a gated mutation past the check (project-kit#82; the adapter's README; Claude Code's "Prompt-free command shape under the sandbox").

### 16. Intermediate files stay in the agent workspace (RS-OPS-016)

**Keep what you write only to get the work done in the agent workspace,** `.agent-workspace/` at the repository root or, in a worktree, the worktree's own, and nowhere else outside the repository. Write there with the file tools, since a shell redirect into it is judged like any other shell write, and remove what you no longer need (the permissions README, "The agent workspace"; project-kit#1043).

## Communicating with the user

### 17. Discuss one decision at a time (RS-OPS-017)

**Discuss one decision at a time, with your recommendation.** When a choice needs the user, surface one decision per turn, not several open questions at once; a summary of work already done is not a decision (project-kit#1648).

### 18. Reference by meaning, then identifier (RS-OPS-018)

**Reference by meaning, then identifier.** Say in plain words what a rule, record or section says, then give its identifier in brackets, as in "a Task must have a parent (DEC-005 P2.1)"; never a bare code, and no glyph such as § (project-kit#13).

## Working across repositories

### 19. A session changes only its own repository (RS-OPS-019)

**A session changes only its own repository.** Never mutate another project's repository from this session without the user's confirmation for that change, whether by changing into it, pointing a command at it (`-R`, `-C`, an absolute path) or otherwise: its files, commits, pushes, issues, pull requests or any of its state. Reading it is fine. Where a cross-repository mutation is meant, stop and ask the user to confirm it or to open a session rooted there, and never do it silently (COR-039).

## Answers on artefacts

### 20. A reviewer checks the answers a change owes (RS-OPS-020)

**A reviewer checks the answers your change owes, and a person, or the delegate they named, decides any other answer on an artefact.** Write the answers `pkit friction check` asks of your change, without asking the person to accept them, and commit them with it, a new answer file among them (COR-062 point 1). Where the check flags a revalidation of yours as replacing others answered apart, make its reason judge their combined state (COR-062 point 7). A reviewer other than you checks them, from the check's own list, never a list you composed (COR-050 point 3). Name an open follow-up in each deferral or `deferred` revisit entry, and say in one sentence what changed in each artefact you revalidated as `updated`, in the pull request or, on a direct commit, to the person you work for. The person who authorises the merge is told these sentences and what is left out of date, until which follow-up, as information. Committing straight to the default branch, have the reviewer, where the project chose one, check before you commit, and tell the person you work for before the commit. Write any other answer, on an artefact or a link's target, or every reason for having no anchors, only once a person accepted it word for word, or the delegate the default branch's configuration names (`friction.delegate`) decided it. The reviewer checks these too, whoever decided them, and blocks the merge, or the direct commit, on an answer or an `updated` sentence that does not hold. Where you can ask neither the person nor the delegate, return the commands and run none (COR-064; the agents README, "Friction writers").

## When a step fails

### 21. Retry once, then stop (RS-OPS-021)

**Retry once a step that failed for a cause outside your own work, then stop.** Such causes include a locked signing key, a service that is down or the network. Check first that the step did not take effect; if it fails again, stop your work and report what failed. Waiting on something pending is not a retry (project-kit#1648).

## Before changing files

### 22. Read the records a change's files lead to first (RS-OPS-022)

**When you change the system, read first the accepted records its files lead to.** Run `pkit refs records-for` once with every file your change will commit, read each record it ties to them directly at the points it names, and read each artefact it reaches them through, the one resting on the fewest records first, following its records that bear on your change. An empty answer is no sign that no record governs a file (the decisions README, "Finding the records a path leads to"; project-kit#2165).

### 23. A choice later work builds on starts with its record (RS-OPS-023)

**Before you make a choice that later work will build on, draft the record that decides it, and let no work rest on the choice until a person accepts the record (COR-065 point 3).** Such choices include a library, an interface or format others use, a convention and a boundary between parts. A change to what an accepted record decides needs a record too. Where your project received that record from elsewhere, follow it in your own files, or propose the change where the record is kept. An accepted rule whose origin states the choice serves as its record. A choice that binds nothing beyond its own change, such as a name or an order inside it, needs no record. Nor does a choice an accepted record already makes. Where you and the person who authorises the merge disagree, that person decides.

### 24. Follow the rule sets' rules on what your change owns (RS-OPS-024)

**Follow the accepted rules that rule sets bind on what your change owns (COR-057 point 2).** Before writing, you may run `pkit rule-sets reach` with your files to see the rules on each one that exists. Before your last commit, run `pkit rule-sets altered` once, and follow each rule it lists as binding: at the head for a file the change adds, edits or brings under a rule, and at the base for one it removes. Where it lists none, this rule asks nothing more. These are the rules the rule-set reviewer judges your change against, and this rule adds none (COR-051 points 4 and 7, COR-057 point 1, [project-kit#2274](https://github.com/aleskalfas/project-kit/issues/2274)).

## Where these rules came from

The split between this file and `.pkit/rules/project.md` is governed by COR-014's universal-applicability principle: rules that apply to any adopting project ship here; rules tied to a specific project's tooling live in the project namespace. A rule that binds only where a capability is installed, such as a work tracker's conventions, is kept in that capability's loaded file, which the capabilities' rules index reaches where the adapter delivers it, not in its documentation (COR-070).
