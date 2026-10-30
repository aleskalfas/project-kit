---
rule-set: OPS
loaded: true
version: 3.0.0
rules:
  RS-OPS-001:
    status: accepted
    origin: {decision: COR-001}
    pkit:
      friction:
        anchors: {record: [COR-001]}
  RS-OPS-002:
    status: accepted
    origin: {decision: COR-066}
    pkit:
      friction:
        anchors: {record: [COR-066]}
  RS-OPS-003:
    status: accepted
    origin: {decision: COR-005}
    pkit:
      friction:
        anchors: {record: [COR-005]}
  RS-OPS-004:
    status: accepted
    origin: {decision: COR-001}
    pkit:
      friction:
        anchors: {record: [COR-001]}
  RS-OPS-005:
    status: accepted
    origin: {decision: COR-010}
    pkit:
      friction:
        anchors: {record: [COR-010]}
  RS-OPS-006:
    status: accepted
    origin: {decision: COR-002}
    pkit:
      friction:
        anchors: {record: [COR-002]}
  RS-OPS-007:
    status: accepted
    origin: {decision: COR-010}
    pkit:
      friction:
        anchors: {record: [COR-010]}
  RS-OPS-008:
    status: accepted
    origin: {date: 2026-06-13, by: "Aleš Kalfas", why: "A destructive operation cannot be undone, so each one waits for the person's own confirmation, given for that operation alone (since the methodology's first release)."}
    pkit:
      friction:
        unanchored-because: "A rule about what an agent asks before an operation that cannot be undone; no record or file carries it out."
  RS-OPS-009:
    status: accepted
    origin: {decision: COR-008}
    pkit:
      friction:
        anchors: {record: [COR-008]}
  RS-OPS-010:
    status: accepted
    origin: {date: 2026-06-13, by: "Aleš Kalfas", why: "An adopter can depend on what a component exposes, so a change to it shows in the component's version, by the project's own bump policy (since the methodology's first release)."}
    pkit:
      friction:
        anchors: {record: [COR-010]}
  RS-OPS-011:
    status: accepted
    origin: {date: 2026-06-13, by: "Aleš Kalfas", why: "A session remembers what was, not what is, so it reads the wiring from the files before it relies on it (since the methodology's first release)."}
    pkit:
      friction:
        unanchored-because: "A rule about how an agent learns the project's state before relying on it, which no core record decides."
  RS-OPS-012:
    status: accepted
    origin: {decision: COR-013}
    pkit:
      friction:
        anchors: {record: [COR-013]}
  RS-OPS-013:
    status: accepted
    origin: {date: 2026-06-13, by: "Aleš Kalfas", why: "An included file nests under the host's heading, so it brings no top-level heading of its own (since the methodology's first release)."}
    pkit:
      friction:
        unanchored-because: "A rule about the form of a file a harness includes, which no core record decides."
  RS-OPS-014:
    status: accepted
    origin: {date: 2026-06-16, by: "Aleš Kalfas", why: "Escaping the sandbox on commands it already permits buries the operator in confirmations, and every adopter needs the rule, so it moved from the project's rules to the core's (project-kit#71)."}
    pkit:
      friction:
        anchors: {record: [COR-028]}
  RS-OPS-015:
    status: accepted
    origin: {date: 2026-06-17, by: "Aleš Kalfas", why: "Compound commands could not be approved automatically, and agents threw away the debugging they rebuilt each time, so the rule asks for the narrowest action the layer can vet (project-kit#82)."}
    pkit:
      friction:
        anchors: {record: [COR-007]}
  RS-OPS-016:
    status: accepted
    origin: {date: 2026-09-28, by: "Aleš Kalfas", why: "Scratch files written outside the repository asked the operator one at a time, so agents keep them in one workspace every profile grants (project-kit#1043)."}
    pkit:
      friction:
        anchors: {record: [COR-028]}
  RS-OPS-017:
    status: accepted
    origin: {date: 2026-10-17, by: "Aleš Kalfas", why: "Several open questions at once make the person parse and re-argue them all, so an agent asks one decision at a time, each with its recommendation (project-kit#1648)."}
    pkit:
      friction:
        unanchored-because: "A rule about how an agent talks with the person; no record or file carries it out."
  RS-OPS-018:
    status: accepted
    origin: {date: 2026-06-14, by: "Aleš Kalfas", why: "A reader should learn what a reference says from the sentence, not by chasing a bare code (project-kit#13)."}
    pkit:
      friction:
        unanchored-because: "A rule about how an agent words a reference to a rule, record or section; no record or file carries it out."
  RS-OPS-019:
    status: accepted
    origin: {decision: COR-039}
    pkit:
      friction:
        anchors: {record: [COR-039]}
  RS-OPS-020:
    status: accepted
    origin: {decision: COR-050}
    pkit:
      friction:
        anchors: {record: [COR-050, COR-062, COR-064]}
  RS-OPS-021:
    status: accepted
    origin: {date: 2026-10-17, by: "Aleš Kalfas", why: "A step that fails for a cause outside the work may pass on a second try, and failing twice means the cause is not passing, so an agent retries once and then stops and reports (project-kit#1648)."}
    pkit:
      friction:
        unanchored-because: "A rule about what an agent does when a step fails for a cause outside its work; no record or file carries it out."
  RS-OPS-022:
    status: accepted
    origin: {date: 2026-10-26, by: "Aleš Kalfas", why: "The records decide the system and the files carry them out, so an agent reads the records a change's files lead to before changing them (project-kit#2165)."}
    pkit:
      friction:
        anchors: {record: ["COR-065#7"]}
  RS-OPS-023:
    status: accepted
    origin: {decision: COR-065}
    pkit:
      friction:
        anchors: {record: ["COR-065#3", "COR-065#1", "COR-064#6", "COR-066#1"]}
---

*Operational rules and tool hygiene shipped by the methodology core, kept as the backbone's loaded rule set `OPS` (COR-068). The loaded file is generated from `.pkit/rule-sets/ops.md`, where the set is authored, by `pkit rule-sets generate`. A project that receives them by sync edits neither (core rule 1). The host `CLAUDE.md` loads it via `@.pkit/rules/core.md`; rationale for each rule lives in the cited record or area README, and a rule neither holds cites the issue that decided it. These rules are operational, not expository — read what a rule cites when its "why" is not obvious, do not violate the rule in the meantime. The file has no top-level heading by design (core rule 13). Project-specific operational rules — those failing universal applicability per COR-014 — live in `.pkit/rules/project.md`. Every layer's rules bind at once: core's, each installed capability's and the project's. A capability's rules and a project's add to core's and never loosen them, and where a rule cannot be kept with one of a layer above it, the upper layer's binds (COR-070).*

## Hard rules

Violating any of these breaks the methodology's invariants. Treat them as gates, not guidelines.

### RS-OPS-001 — The no-shared-files invariant

**The no-shared-files invariant.** Every file has exactly one owner — the methodology core or the project. Never edit core-owned files; edits are silently overwritten by `pkit sync`. To extend content, add sibling files in the matching `project/` directory (or in the file the adapter merges into). See `.pkit/decisions/README.md`.

### RS-OPS-002 — The acceptance gate

**The acceptance gate.** Only act on `accepted` decisions. Proposed records are draft hypotheses. Do not author dependent code, docs, or downstream decisions citing a proposed record — accept it first (one-line status flip + commit) or pause. See `.pkit/decisions/README.md`.

### RS-OPS-003 — Author core-shipped artifacts through the paired skill or `pkit new`

**For authoring core-shipped artifacts (decisions, adapters, migrations, areas, scratchpad notes, agents, capabilities), invoke the paired skill or call the underlying `pkit new <kind>` command directly — never hand-stamp the file.** The script enforces correct numbering, frontmatter, and layout deterministically; the skill enforces the disciplines. See COR-005 ("Skill / command pairing") and `.pkit/cli/README.md`'s "Authoring commands" section for the current set of paired skills.

### RS-OPS-004 — PRJ records live in `.pkit/decisions/project/`

**PRJ records live in `.pkit/decisions/project/`; never edit `.pkit/decisions/core/`.** Core records are managed by the methodology source and refreshed on every sync. Numbering is independent across the two namespaces. See `.pkit/decisions/README.md`.

### RS-OPS-005 — Migrations are idempotent and safe over any state

**Migrations are idempotent, and a backbone migration is safe over any state.** If you author a migration script, it must be safe to re-run on already-migrated state — detect already-applied state and exit cleanly. A backbone migration also acts only on a positive sign that its change is needed, and never deletes by a path's name or position alone. A version transition may run it again over a project whose migration history is unknown. A missing default the migration adds counts as a positive sign, so running it again may restore a default the project removed after it first ran. If your script adds a missing default, say so in the release's notes. See COR-010 and `.pkit/lifecycle/README.md`'s "Migration framework → Script contract".

### RS-OPS-006 — Settings-file changes go through the merge primitive

**Settings-file changes go through the merge primitive.** Do not edit fixed-path config files (`.claude/settings.json`, `.gitignore`, etc.) directly to add core-shipped content; the adapter merges baseline + project additions. Edit only the project-additions side. See COR-002.

### RS-OPS-007 — Surface changes ship a migration in the same change-set

**Surface changes ship a migration in the same change-set.** A change that alters an installed adopter's state observably and breaks against it — file or directory renames / removals in kit-owned trees, schema_version bumps in YAML schemas, breaking CLI signature changes, capability subtree restructures — must include a migration script at the affected tier (backbone / adapter / capability) in the same commit or PR. The migration is idempotent (per core rule 5). Pure additions, documentation refinements, behaviour-preserving fixes don't trigger. Before committing, check the diff for triggers; `pkit migrations check-diff` verifies coverage; CI gates the merge. See COR-010 ("Migrations are mandatory on adopter-breaking surface changes").

## Tool hygiene

Operational practices that keep work consistent and recoverable.

### RS-OPS-008 — Pause and confirm before destructive operations

**Pause and confirm before destructive operations.** `git reset --hard`, `git push --force`, deleting files outside `project/`, dropping database tables, killing processes, `rm -rf` — all warrant explicit confirmation from the user, even when the task seemed to authorize them generally. Authorization for one destructive op is not authorization for the next.

### RS-OPS-009 — Conventional commits, one logical unit each

**Use conventional commits and keep one logical unit per commit.** The branch-naming convention, `<type>/<issue-number>-<slug>`, is COR-008's: see its "Operational reference" section for the recommended type list, the convention and its examples.

### RS-OPS-010 — Surface changes bump the version of the affected component

**Surface changes bump the version of the affected component.** A change that an adopter could observe, depend on, or break against is a *surface change*; documentation refinements and internal refactors are not. The exact bump policy is per-project (each project records its policy as a PRJ record); each component adopts analogous rules.

### RS-OPS-011 — Validate before assuming state

**Validate before assuming state.** Use `pkit status` to see how the methodology is wired in this project (paths, adapter, deployed skills, capabilities, decision counts). Don't infer state from prior sessions; the file system is the source of truth.

### RS-OPS-012 — Skills and agents are deployed by the adapter

**Skills and agents are deployed by the adapter, not hand-symlinked.** The adapter's deploy primitives (e.g. `deploy-skills.sh` and `deploy-agents.sh` for Claude Code, the second per COR-013) deploy canonical content from `.pkit/skills/` and `.pkit/agents/` into the harness's expected location: skills as symlinks, agents as copies with their overlay placeholders resolved. Editing the deployed symlinks or copies instead of the canonical core-side file violates the no-shared-files invariant.

### RS-OPS-013 — An included file has no H1

**Files intended for `@<path>` include omit the H1 and start with prose or H2 sections** *(applies when using the Claude Code harness; other harnesses have different include mechanisms documented in their adapter README)*. The host file owns the H1; the included content nests under it. Place the `@<path>` line after the host's intro paragraph, not at line 1, so the included sections become natural sub-sections of the host. The loaded file, `.pkit/rules/core.md`, is the canonical example: no H1, opens with an italic preface, sections start at H2; CLAUDE.md includes it after its own intro.

### RS-OPS-014 — Don't escalate past the permission model

**Don't escalate past the permission model for commands it already permits.** When a project runs a permission model and a confinement sandbox, both are configured so that allowlisted domain commands — version control, the issue tracker, the kit CLI — run with the network egress and scratch-file access they need *inside* the sandbox, auto-approved with no prompt. Reaching for a sandbox-escape or permission-escalating flag on such a command forces a manual operator confirmation *by design* and overrides that auto-approval — so doing it reflexively on routine work buries the operator in avoidable confirmations (a single session has produced dozens). Run the command as-is and let the model approve it; reserve any escape/escalation flag for the rare command that genuinely cannot run within the model. *(The escape mechanism is harness-specific — e.g. the Claude Code harness's sandbox-disable flag; other harnesses differ. What the sandbox permits is set by the confinement toolkits, which `pkit permissions sandbox toolkit list` shows.)* The rationale lives in the permission model's records (COR-028 and its ADRs).

### RS-OPS-015 — Work with the permission layer, not around it

**Work with the permission layer, not around it.** Issue the narrowest action that layer can vet and auto-approve: a single, simple command rather than a compound that bundles several operations into one opaque step the layer must approve whole. Prefer the harness's dedicated read / search / write tools over ad-hoc shell for inspection. When a diagnostic recurs or is non-trivial, extract it into committed project tooling — a named command the project owns — rather than re-deriving a throwaway script each time; that is COR-007's pattern-extraction applied to debugging, turning disposable complexity into one clean, reusable, reviewable invocation. And never compose a command to *evade* the intent layer's gated mutations: slipping a denied operation past the check by wrapping it defeats the control, and the validated path exists precisely so the mutation is checked. *(What counts as a single auto-approvable action, and any script-composition mechanic, is harness-specific — documented in the harness's adapter; the Claude Code adapter is the worked example.)* Same confirmation-fatigue-and-lost-work rationale as core rule 14.

### RS-OPS-016 — Intermediate files stay in the agent workspace

**Keep intermediate files in the agent workspace, and nowhere else outside the repository.** What an agent writes only to get its work done — a pull-request or issue body, a script, captured output, review notes — goes in the workspace: `.agent-workspace/` at the repository root. A worktree has its own, at its root; another repository's workspace is off limits under the cross-repository rule (core rule 19). The methodology's install and sync create the folder and exclude it from version control through the repository's local exclude file, so nothing in it reaches a commit. Reading, creating and editing files there with the harness's file tools is granted by every shipped profile, so write intermediate files there with the file tools; a shell redirect or here-document into the folder is judged like any other shell write. A write anywhere else outside the repository asks, one file at a time, for the whole session, until the operator approves a stream of harmless confirmations without reading them — the confirmation fatigue the permission model exists to prevent (COR-028). Remove what you no longer need. *(How a harness is made to approve the folder is the adapter's concern; the grant and the harness-neutral contract are the permission model's, which the backbone ships — see `.pkit/permissions/README.md`.)* Rationale and field note: [project-kit#1043](https://github.com/aleskalfas/project-kit/issues/1043).

## Communicating with the user

How an agent talks with the user, independent of any project's tooling.

### RS-OPS-017 — Discuss one decision at a time

**Discuss one decision at a time, with your recommendation.** When a choice needs the user's input, surface a single decision per turn, with what you recommend ([project-kit#1648](https://github.com/aleskalfas/project-kit/issues/1648#issuecomment-6247728164)) — don't stack several open questions or unknowns into one message. A wall of simultaneous decisions forces the user to parse and re-litigate everything at once; a stepped conversation is faster and clearer. This applies to discussion and decision-making, not to summaries of work already done.

### RS-OPS-018 — Reference by meaning, then identifier

**Reference by meaning, then identifier.** When pointing at a rule, record, or section, state what it actually says in plain language first, then put the identifier in brackets after — "a Task must have a parent (DEC-005 P2.1)". A precise sub-locator is welcome; just write it without cryptic glyphs (no §), and never reference by bare code alone. The reader should learn the substance from the sentence, not have to chase the reference.

## Working across repositories

How a session relates to repos other than the one it is rooted in.

### RS-OPS-019 — A session changes only its own repository

**A session mutates only its own repo's context; cross-repo mutation is an operator-gated exception.** A session is rooted in one project's repo and carries *that* repo's governance — its rules, conventions, deployed agents, permission model. Do **not** mutate a *different* project's repo from inside this session by changing directory into it, redirecting a command at it (`-R`, `-C`, an absolute path), or any equivalent: the other repo's governance never loads, so the mutation runs under the wrong project's context (the session-level analogue of editing a file a repo doesn't own — core rule 1, one altitude up). *Reading* another repo is fine; the line is at mutation (file writes, commits/pushes, issue/PR changes, decision/state authoring) whose target is the other repo. When a cross-repo mutation is genuinely intended, **stop and surface it to the user** — "this targets a different repo; open a session rooted there, or confirm the cross-repo override" — and never perform it silently. The methodology CLI and its capability scripts enforce this where they own the mutation (refuse-or-prompt on a context-mismatch); this rule covers the paths no methodology code interposes on (a raw `git`/`gh`/shell command). The guard is an honest **interlock against accidental handoff, not a security boundary** — a determined raw command can bypass it, which is exactly why the discipline matters. Rationale and the realization detail live in COR-039 and the ADR that realizes it.

## Answers on artefacts

### RS-OPS-020 — A reviewer checks the answers a change owes

**A reviewer checks the answers your change owes, and a person, or the delegate they named, decides any other answer on an artefact.** Write the answers the change check (`pkit friction check`) asks of a change you are making, without asking first. Commit what the writers write with your change, a new answer file among it (COR-062 point 1). Where the check flags one of your revalidations as replacing revalidations answered apart, make that revalidation's reason judge their combined state (COR-062 point 7). A reviewer other than you checks your answers, from the change check's own list, never a list you composed, and blocks the merge when an answer does not hold (COR-050 point 3). Name an open follow-up in the reason of each deferral, or `deferred` revisit entry, you write. For each artefact you revalidated as `updated`, say what changed in it, in one sentence, in the pull request or, on a direct commit, to the person you work for. The reviewer blocks the merge, or the direct commit, when that sentence is missing or does not match what changed. Do not ask the person to accept these answers. The person who authorises the merge is told the sentences and what is left out of date, until which follow-up, as information, not a gate. Committing straight to the default branch, have the reviewer, where the project chose one, check before you commit, and tell the person you work for. Any other answer, on an artefact or for a link's target your change was not asked about, and every reason for having no anchors (COR-050 point 1), is written only after a person was shown it word for word and accepted it, or the project's delegate decided it. The delegate is the agent the default branch's configuration names (`friction.delegate`), and it never decides an answer it drafted (COR-064). The reviewer checks these answers too, whoever decided them. If you can ask neither the person nor the delegate, return the commands and run none. Details: the agents README, "Friction writers".

## When a step fails

### RS-OPS-021 — Retry once, then stop

**Retry once a step that failed for a cause outside your own work, then stop.** Such causes include a locked signing key, a service that is down or the network. Before the retry, check that the step did not take effect. If it fails again, stop your work and report what failed. Waiting on something pending is not a retry. Rationale: [project-kit#1648](https://github.com/aleskalfas/project-kit/issues/1648#issuecomment-6247728164).

## Before changing files

### RS-OPS-022 — Read the records a change's files lead to first

**When you change the system, read first the accepted records its files lead to.** The records are where the system is decided, and the files carry those decisions out. Run `pkit refs records-for` once, with every file your change will commit, and read each record it lists as tied to them directly, at the points it names. Where it reaches a file only through another artefact, read that artefact, the narrowest first, and follow the records it rests on that bear on your change. An empty answer is no sign that no record governs a file. What the lookup reads, and why: the decisions README, "Finding the records a path leads to" ([project-kit#2165](https://github.com/aleskalfas/project-kit/issues/2165)).

### RS-OPS-023 — A choice later work builds on starts with its record

**Before you make a choice that later work will build on, draft the record that decides it, and let no work rest on the choice until a person accepts the record (COR-065 point 3).** Such choices include a library, an interface or format others use, a convention and a boundary between parts. A change to what an accepted record decides needs a record too. Where your project received that record from elsewhere, follow it in your own files, or propose the change where the record is kept. An accepted rule whose origin states the choice serves as its record. A choice that binds nothing beyond its own change, such as a name or an order inside it, needs no record. Nor does a choice an accepted record already makes. Where you and the person who authorises the merge disagree, that person decides.

## Where rationale lives

Each rule cites the record or doc that owns its "why", or, where none does, the issue that decided it. The umbrella references:

- `.pkit/decisions/README.md` — the schema, statuses, the no-shared-files invariant, the acceptance gate.
- `.pkit/decisions/core/COR-NNN-*.md` — accepted core records; each captures a principle with rationale.
- `.pkit/lifecycle/README.md` — the manifest schema, upgrade procedure, migration framework.
- `.pkit/cli/README.md` — the CLI surface and per-command behaviour.
- `.pkit/adapters/README.md` and per-adapter READMEs — harness translations.

## Where these rules came from

The split between this file and `.pkit/rules/project.md` is governed by COR-014's universal-applicability principle: rules that apply to any adopting project ship here; rules tied to a specific project's tooling live in the project namespace. A rule that binds only where a capability is installed, such as a work tracker's conventions, is kept in that capability's loaded file, which the capabilities' rules index reaches where the adapter delivers it, not in its documentation (COR-070).
