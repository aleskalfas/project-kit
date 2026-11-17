---
id: DEC-021
title: Team membership gate — pm operations check a member list before mutating; open mode bootstraps; closed mode locks
status: accepted
date: 2026-05-24
author: Ales Kalfas
---

## Context

The capability's authority model today trusts the invoker. [project-management:DEC-008-pm-and-implementer-roles] distinguishes PM and Implementer roles for *what* operations are appropriate, but every command treats whoever runs it as authorised to do the role's work. The two evolving operation sets (the verb-subject scripts pinned by [project-management:DEC-020-methodology-as-executable-commands] and the prerequisite/setup/migrate trio from [project-management:DEC-017-prerequisites-bootstrap-migrate-discipline]) inherit the same trust model — anyone with repo access can invoke them.

This works for single-repo private projects where everyone with access is on the team. It fails for **public-org repos where many people have read or write access but only a subset of the team actually does project-management work**. Without a membership gate, anyone in the org can mediate the methodology — file structurally-wrong issues, mis-classify, mass-transition states, mis-shape titles. The methodology gets diluted; the team's signal weakens.

The user's framing captures the requirement: *"if there isn't yet [a member list] all can manage. If there is, just people from the list can work with project management; others should be added by someone from the list."* A first-member bootstrap (open mode → first add → closed mode), with self-add only while open, and adds via PR review by an existing member thereafter. The pattern has prior art in pm-workflow's **Quorum** convention — a maintained list of authoritative people; ops gate on membership.

A separate full design walk for the membership mechanism (canonical-from-main vs working-tree read, identity resolution across surfaces, removal authority, lockout recovery) is **deferred**. This DEC pins the principle, the v1 file shape, and which surface names the invoker where the hosting service answers that the credential the commands write to the tracker with, called *the credential* below, acts as a user's account; the other mechanism details land alongside the implementing PR.

## Decision

Every run of a pm command that can write ([project-management:DEC-073-reads-take-no-gate] point 1), its dry runs included, checks a project-side **`members.yaml`** file before proceeding, while a command that only reads and reports takes no membership gate (refinement per [project-management:DEC-073-reads-take-no-gate]). The check has two modes: open (the file is absent or empty — any invoker passes) and closed (the file lists ≥1 member — only listed members pass). The first member adds themselves while open mode applies; from that gesture forward the file is closed. Where the hosting service answers that the credential acts as a user's account, that account is the invoker, for the check and for every command that names who runs it ("Identity resolution").

### File location and shape

The members file lives at **`.pkit/capabilities/project-management/project/members.yaml`** — project-side per the no-shared-files invariant, adopter-owned, committed to main, schema-validated against a kit-shipped `schemas/members.schema.json` companion.

V1 shape (per-entry shape may add fields later as needs surface; v1 commitments are below):

```yaml
schema_version: 1
members:
  - github_login: aleskalfas
    name: Ales Kalfas
    email: kalfas.ales@gmail.com
    role: PM                  # optional; PM | Implementer; default Implementer
    added_at: 2026-05-22
    added_by: bootstrap       # "bootstrap" for first member; GitHub login of adder otherwise
```

`github_login` is the canonical identity, which for a user's account is the login as the hosting service spells it; `name` + `email` are present for multi-surface identity resolution and human readability. `role` is informational at v1 (DEC-008 already distinguishes the roles); enforcement of role-specific ops gating is out of v1 scope and follows COR-007 if the recurrence appears.

### Two modes; the predicate

- **Open mode** — `members.yaml` is absent, or present with an empty `members:` list. The predicate **passes for any invoker** with repo access. This is the bootstrap state.
- **Closed mode** — `members.yaml` is present with ≥1 member. The predicate **passes only if** the invoker's identity matches an entry. Non-members get a structured refusal:

  ```
  [refused] Membership required for `<verb> <subject>` operation
            → This repository is in closed mode (.pkit/capabilities/project-management/project/members.yaml has ≥1 entry).
            → Your identity (<github-login>) is not in the member list.
            → Remediation: ask an existing member to add you via `add-member.py`.
  ```

The predicate runs at script startup, before any other work. Membership is not re-checked mid-operation.

### Bootstrap: the first member self-adds

While open mode applies, anyone with repo access may run `add-member.py` to add themselves. The PR landing the first member entry is reviewable by anyone with repo access — there is no "existing member" to review it yet. From the moment the first entry lands on main, the repo is in closed mode, and subsequent member additions require an existing member's review on the adding PR.

The first member's `added_by:` field is the literal string `bootstrap` to mark the seed event.

### Membership change authority

- **Adding members** — an existing member authors the change (`add-member.py` stamps an entry; the actual landing is via PR). The PR requires review by ≥1 existing member who is not the author. The first-member exception above applies only when open mode applies.
- **Self-removal** — a member removes themselves; the change is reviewable by any other member.
- **Removing another member** — any member authors; the PR cannot be approved solely by the author.
- **Lockout recovery** — if all members are removed (legitimately or by accident), the repo re-enters open mode. Anyone with write access via GitHub's permissions can then edit the file directly and the cycle restarts.

The git history of `members.yaml` IS the audit trail; no extra audit machinery ships.

### Identity resolution

The predicate resolves the invoker's identity from three surfaces, in order:

1. **`gh api user --jq .login`** — primary; matches the methodology's GitHub-bound substrate from [project-management:DEC-003-github-bound-substrate]. Where the hosting service answers that the credential acts as a user's account, that account's login alone is the invoker's identity: neither surface below stands beside it or in its place.
2. **`git config user.email`** — fallback when `gh` is unavailable.
3. **Process-environment variable** — `PM_INVOKER_LOGIN` reserved for CI / agent contexts where the natural sources don't apply; sourced from a CI secret or workflow input, never from user-controllable env.

`members.yaml` lists `github_login` + `email` per entry. A user's login the hosting service answers for the credential passes only where an entry's `github_login` names it, whatever git's email and `PM_INVOKER_LOGIN` name. Where the service does not answer that the credential acts as a user's account, the match is positive if any surface's resolved value matches any entry's corresponding field.

Every other reader of the invoker's identity, such as the filer an issue's assignee defaults to, takes the same login: where the service answers that the credential acts as a user's account, each command names that account wherever it names who runs it, and never a person `PM_INVOKER_LOGIN` names in its place (Implications, "Every reader of the invoker's identity").

The detailed mechanics — canonical-from-main vs working-tree read, fail-open vs fail-closed on network errors, caching — are **deferred** to the implementing PR. The principle is: closed mode prefers the authoritative `members.yaml` as committed to main, with a sensible fallback the implementing PR makes explicit.

### Tooling surface

Three verb-subject scripts ship under [project-management:DEC-020-methodology-as-executable-commands]'s convention:

- `scripts/add-member.py` — stamp a new entry. Validates invoker is a current member (or that open mode applies). Writes the entry; commits to a working branch the user opens a PR from.
- `scripts/remove-member.py` — stamp the removal. Same constraints.
- `scripts/show-members.py` — read-only inspection; lists the current members + their roles.

Every other pm command, a verb-subject script or not, save one that only reads and reports, gains a **membership predicate check at startup** — the first thing the command does after parsing args, on every run, its dry runs included. Open mode bypasses; closed mode applies the closed-mode predicate above. A command only reads and reports where no run of it writes (refinement per [project-management:DEC-073-reads-take-no-gate]).

A shared library (`scripts/_lib/membership.py` or equivalent) holds the predicate so every script invokes the same implementation.

### Sequencing

The principle lands at **v0.3.0** as a stub: the predicate library + the file shape + the read-only check; bootstrap mode active by default. The management commands (`add-member.py`, `remove-member.py`, `show-members.py`) land alongside `create-issue.py` + `validate-issue.py` in v0.3.0 so the first verb-subject scripts have a complete authority story.

Cross-repo membership coordination (a `members_source:` field pointing at a central governance-repo file) is out of v1 scope; that interaction lives with the methodology-mesh design.

## Rationale

**Why a member list rather than relying on GitHub repo permissions.** GitHub permissions are coarse — `read`, `write`, `admin`, applied across the whole repo. Methodology authority is finer-grained: someone can have write access for code contributions without being authorised to mediate the methodology's issue lifecycle. A separate `members.yaml` lets the methodology declare its own authority surface without conflating it with code-write authority. It also makes membership *visible in main* — a reviewer can audit the team without invoking the GitHub API.

**Why open mode for empty / absent file.** Bootstrap chicken-and-egg: someone has to be the first member, and they cannot be approved by an existing member who does not yet exist. The empty-file-is-open convention lets the first member self-add. The cost is that an unconfigured repo has no methodology authority gate at all — but an unconfigured repo also has nobody on the team to be gated against, so the cost is theoretical until the first add.

**Why review-by-an-existing-member for closed mode.** Trust within the team is symmetric — any existing member's review is sufficient. Asking for quorum, role-specific approvers, or a separate review-agent at v1 is over-design before there's evidence the simple rule fails. COR-007 says wait for recurrence; promote to richer authority models if real cases demand them.

**Why role is informational at v1.** [project-management:DEC-008-pm-and-implementer-roles] already names PM vs Implementer as a role distinction in prose; encoding it in `members.yaml` makes the assignment visible. But gating role-specific ops (e.g., refusing EPIC filing from an Implementer) on the role field is a separate enforcement decision. Doing it at v1, before there's evidence of frequent role-confusion, risks codifying the wrong gates. The role field is present so the assignment is visible; enforcement is a future refinement.

**Why git history as the audit trail.** Every `members.yaml` change is a PR landing on main with author, reviewer, commit message, and date. Recreating that audit in a separate ledger duplicates state; trusting git history keeps the methodology lean.

**Why a user's login the hosting service answers stands alone.** That login names the user's account the credential acts as, whose writes reach the tracker; changing it takes holding another account's credential. Git's email and `PM_INVOKER_LOGIN` are settings of the machine, made by its user or its setup, which may name anyone. Beside that login, such a setting can only agree with it or name another account, and where it names another, it would pass or refuse the acting account on a value the gate cannot check: a session whose credential acts as a user's account kept for a workflow, on a machine whose git configuration or setup names a member, would pass the gate though its own account is no member's. That argument alone keeps the variable from standing beside a user's login the service answered. For git's email, the section's order says the same: the email is a fallback "when `gh` is unavailable", as the member list's schema also describes it, and a `gh` that answers with a user's login is not unavailable. Where the service does not answer that the credential acts as a user's account, whether it answers with an app's account, refuses, or cannot be asked, this record decides there only the match on any surface that the paragraph on matching states; whether git's email and the variable should name the invoker there rests on evidence of its own ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)). The gate is no wall against someone set on passing it, who can write to the tracker without the commands; it keeps the methodology's operations with the people the list names, and a setting that names a member by accident would defeat that without anyone meaning it to.

**Why every reader of the invoker's identity takes that login.** The argument above is the gate's, and a reader that grants nothing by naming a person needs one of its own. That reason is one account for each run: the assignee a command writes, the author of each comment it posts and the actor its moves hand the engine then name the same account, the one the credential acts as, in every clone and every project. A person who wants the work in their own name gives the agent their own credential, and the agent's pull requests are then the person's own, which the person cannot approve ([project-management:DEC-028-agent-as-approver-paths], "Self-approval degrade"). A name beside that account would split the assignee, the authors and the actor, and where a reader judges what that account writes, the split breaks the reader:

- **The engine's actor** is the actor a gate judges, and an authorisation the gate confirms must come from an authority other than that actor ([pkit:COR-033] P4). For the move to Done, that authorisation is the pull request's merge, which the capability's gate command reports for the engine to judge ([project-management:DEC-033-rebind-issue-lifecycle-onto-process-substrate] D4). An actor taken from the variable reads the acting account's own merge as another authority's.
- **A claim on work,** which a clone writes only where it holds an instance id ([project-management:DEC-035-instance-ownership] point 1), counts only from the assignee's account ([project-management:DEC-043-ownership-substrate-selection] point 3). There, an assignee taken from the variable, under a credential that acts as another user's account, leaves each claim that account writes uncounted, so the Task's instance ownership breaks.
- **A seat's holder,** where the project keeps a topology of seats, is the author of its claim on the seat's state issue, as GitHub records the comment ([pkit:ADR-071] point 4). A clone that names itself by the variable does not find itself holding the seat its own account claimed.

**Why mechanism details are deferred.** The five questions left open — canonical-from-main vs working tree, fail-open vs fail-closed on network errors, identity resolution edge cases, removal vs deactivation, multi-repo central membership — each have legitimate trade-offs that benefit from being decided alongside the implementing PR's actual code, not in advance. The DEC pins the principle and the file shape; the implementing PR pins the mechanics. Which surface names the invoker where the hosting service answers that the credential acts as a user's account is no edge case: it decides who passes the gate and whom every command names as the invoker, so the DEC pins it ("Identity resolution").

### Alternatives considered

- **Rely solely on GitHub repo permissions.** Rejected — coarse-grained, not visible in main, conflates code-write authority with methodology authority.
- **CODEOWNERS file as the gate.** Rejected — CODEOWNERS gates code review, not methodology mediation. Different surface; mixing the two breaks both.
- **Quorum-of-N approval per pm operation.** Rejected at v1 — over-design before evidence. The capability's mutating operations land in PRs that already have review; per-op quorum is duplicate friction.
- **Role-strict gating (Implementer can't file EPICs).** Rejected at v1 — the role distinction is informational until recurrence proves the gate is worth the friction.
- **Bootstrap requires admin self-add via a privileged command.** Rejected — over-engineered for the chicken-and-egg case; open mode is simpler and visible.
- **Git's email beside a user's login the hosting service answered, or `PM_INVOKER_LOGIN` in its place.** The case: a member whose entry names another of their logins, such as a renamed or a second account, passes by email; a workflow under a user's account kept for it passes by the variable naming a member, without that account being added; and the service is not asked where the variable is set. Rejected — each passes an account the list does not name, by a setting of the machine, by accident as readily as by intent ("Why a user's login the hosting service answers stands alone"). A wrong login in an entry is mended in the list, and an account a workflow acts as is added like any member.
- **`PM_INVOKER_LOGIN` beside a user's login the hosting service answered, for the readers that grant nothing:** the filer an issue's assignee defaults to, and the current user `start-work` compares a Task's assignee with, while the gate reads the answered login alone. The case: a setup under a user's account kept for a workflow assigns the work to the person the agent works for, not to that account. Rejected — the assignee would name another account than the author of each write and the engine's actor, and where the clone holds an instance id, a Task assigned to the variable's person carries claims from the acting account that never count, so its instance ownership breaks ("Why every reader of the invoker's identity takes that login"). A person who wants the work in their own name gives the agent their own credential, at the cost that section names.
- **`PM_INVOKER_LOGIN` beside a user's login the hosting service answered, only for the readers that say whose work it is, and only where the clone holds no instance id:** the filer an issue's assignee defaults to, the account `--me` names on an assignment, and the current user `start-work` compares a Task's assignee with and assigns. The readers that write as the account or are judged by what it writes, such as the gate, a claim, a seat's holder and the engine's actor, take the answered login. The case: a clone with no id writes no claim, so none goes uncounted, and the person the agent works for keeps the work in their own name. Rejected — a user's account can be the assignee, so under one credential a Task's assignee would name another account than the author of each write and the engine's actor, and its assignee and its history disagree.
- **`PM_INVOKER_LOGIN` as a second check beside a user's login the hosting service answered,** refusing where it names another account. The case: an agent that works for a non-member, under a member's credential, is refused. Rejected — the variable is the caller's word, so it refuses only a setup that names the non-member truthfully, and the session acts as the member whose credential it holds.

## Implications

- **Every pm command, a verb-subject script per DEC-020 or not, save one that only reads and reports,** invokes the shared membership predicate at startup. Open mode bypasses; closed mode refuses non-members with the closed-mode refusal template above (refinement per [project-management:DEC-073-reads-take-no-gate]).
- **The capability `version:`** bumps to v0.3.0 on the implementing PR (the stub + the three management scripts + the predicate library).
- **The `schemas/members.schema.json`** validates `members.yaml` against the shape above. Adding fields is a same-PR-as-surface-change discipline per [project-management:DEC-017-prerequisites-bootstrap-migrate-discipline]'s `schema_version` bump rule.
- **Bootstrap state is the install default** — a fresh `pkit capabilities install project-management` leaves `members.yaml` absent. First-time adopters use `add-member.py` to seed it; the first add is the moment the repo transitions to closed mode.
- **The project-manager** does not need to know membership — the verb-subject scripts enforce. If an agent runs on behalf of a non-member's chat session, the scripts that take the gate refuse where the identity the gate reads is no member's, and the agent surfaces the refusal (refinement per [project-management:DEC-073-reads-take-no-gate]). Where the hosting service answers that the credential acts as a member's user account, the session acts as that member, whoever it works for.
- **CI invocations** of verb-subject scripts and of the other pm commands, save those that only read and report (refinement per [project-management:DEC-073-reads-take-no-gate]), authenticate as a service identity that is added to `members.yaml` like any other member, or, where the hosting service does not answer that the workflow's credential acts as a user's account, set `PM_INVOKER_LOGIN` from a CI secret. CI is not exempt from the gate by design. An invocation of a command that only reads and reports needs no entry in `members.yaml` and no `PM_INVOKER_LOGIN`, behind a closed gate as behind an open one (refinement per [project-management:DEC-073-reads-take-no-gate]).
- **Every reader of the invoker's identity** takes, wherever the hosting service answers that the credential acts as a user's account, that account's login, as the predicate does ("Why every reader of the invoker's identity takes that login"). Among them are the filer an issue's assignee defaults to ([project-management:DEC-019-mandatory-issue-state], "Mandatory assignment"), and the current user `start-work` compares a Task's assignee with ([project-management:DEC-026-work-ownership-lifecycle], "The seven commands"). The capability's documentation, where it says how the invoker's identity is resolved, lists every reader.

  So a session whose credential acts as a user's account kept for a workflow files, takes and starts work, claims it, moves issues, comments, holds seats and adds itself to the member list as that account, whoever `PM_INVOKER_LOGIN` names, in every project, the gate open or closed. A bootstrap under such a credential makes that account the first member, and the engine's gate reads that account's own merge as its own, not as another authority's. That is the rule's cost under such a credential: starting work refuses a Task assigned to the person the agent works for, as one assigned to someone else, and new work is assigned to that account, not to that person.
- **The email beside the login on an audit comment** comes from the audit-comment template ([project-management:DEC-014-validation-severity-model]), and is no part of the invoker's identity. Where git's configuration on the machine names someone other than the user's account the credential acts as, the comment then pairs that account's login with that person's email. This record names that mixed stamp as a cost, and leaves the template's email to DEC-014.
- **The request for the account.** Resolving the invoker's identity asks the hosting service which account the credential acts as, whether or not `PM_INVOKER_LOGIN` is set. Each such request counts against the service's limits on requests, which matters where many agents run at once.
- **Whom a closed gate refuses.** Where the service answers that the credential acts as a user's account no entry names, a closed gate refuses, whatever git's email and `PM_INVOKER_LOGIN` name. So it refuses a member whose entry names another of their logins, until the entry is mended or they sign in as the listed account. It refuses a session whose credential acts as a user's account kept for a workflow, until that account is added.
- **Cross-repo membership** (a shared `members.yaml` across a team's repos) is out of v1 scope; the cross-repo coordination of `members.yaml` content is in the methodology-mesh design's scope.
- **A future kit-level COR may generalise the membership pattern** if a second capability adopts an equivalent gate. Promotion follows COR-007.
