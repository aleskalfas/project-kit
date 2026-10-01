---
id: ADR-061
title: Landing a pull request on the hosting service lives once, in the backbone
status: proposed
date: 2026-10-01
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** everything the methodology does on the hosting service to land a pull request is implemented once, in the backbone: reading where the PR stands with its base branch's merge queue, merging it, handing it to the queue, waiting for the queue and taking it out again. The backbone offers it as the `pkit pull-request` command. A capability's scripts call that command, and the backbone's own commands import the module behind it. It works only for GitHub, through `gh`, and says so. It reads no host from any configuration, because the caller's environment decides which host `gh` reaches. It stays out of `pkit repository`, which remains a local reading that uses no network. The command makes the requests. Each caller keeps the decisions: when to land, and what happens after the merge. Each caller also keeps four obligations that no single command can keep for it. Its versioned JSON documents are the contract. Its mutating subcommands run the cross-repository guard themselves. The backbone's way of landing, one squash commit carrying the PR's title and body, is grounded in this record, not in a capability's.

## Context

Two commands land pull requests: project-management's merge verbs and the backbone's `pkit release merge`. A merge queue makes landing subtle. A merge request that succeeds may only have put the PR in the queue. A push after the checks ran must take the PR back out. And the queue builds the squash commit from repository settings, ignoring what the merge request passes. Two copies of this mechanic drifted apart, at a real cost: one took a successful merge request for a merge and deleted the head branch of a PR the queue had only taken in, which closes the PR and drops it from the queue (#1200). The queue is also the intended single path for merging ([ADR-055](ADR-055-first-adopter-analysis-and-living-docs.md) point 5), so every landing will meet these subtleties. The mechanic now lives in one backbone module, [`pull_request_landing`](../../../src/project_kit/pull_request_landing.py), offered as the public command `pkit pull-request`.

This is the backbone's first general command that acts on a hosting service. No record yet answers the questions it raises:

- where such acts belong;
- how they relate to `pkit repository`, which is local and uses no network ([COR-054](../../../.pkit/decisions/core/COR-054-default-branch.md));
- what tying a core command to one service means, when core content is meant for any adopter ([COR-014](../../../.pkit/decisions/core/COR-014-universal-applicability.md));
- where the host comes from;
- what the command cannot do for its callers;
- whether it guards against mutating another repository ([COR-039](../../../.pkit/decisions/core/COR-039-session-repo-mutation-boundary.md)).

The one decision that put the mechanic in the backbone sits in a capability record, project-management's [DEC-013](../../../.pkit/capabilities/project-management/decisions/DEC-013-branch-and-pr-conventions.md) ("Merge mechanics"). The backbone's module and references cite it as their authority. That leaves the backbone resting on a record of a capability that an adopter may never install.

## Decision

**The acts that land a pull request on the hosting service have one home: the backbone's `pull-request` command, realised for GitHub through `gh`. Callers keep their own decisions and four obligations. The JSON documents are the contract. The command guards the changes it makes.**

1. **One home.** The acts that land a pull request are computed in one backbone module and nowhere else. They are: reading where the PR stands with its base's merge queue; reading the repository's squash-commit defaults; the direct squash merge and the enqueue, each pinned to the head the caller checked; the wait for the queue's merge; and taking a PR out of the queue. Capability scripts reach the module through `pkit pull-request --json`, as they reach the backbone's other engines by command ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 1; COR-054 point 5). The backbone's own commands import it. No caller asks `gh` for one of these acts itself. What a caller reads to decide *whether* to land (checks, approvals, mergeability) stays the caller's own.

2. **Separate from `repository`.** `pkit repository` answers from local git references, uses no network, and gives the same answer in every clone (COR-054 points 2 and 5). A pull request's state is a fact held by the hosting service: it is read over the network and can change between two readings. So the two commands stay apart:
   - nothing under `repository` reaches the hosting service;
   - a reading of the default branch never falls back on the service's answer (COR-054 point 4);
   - no command bound by the query contract (bounded, deterministic, needing no network; ADR-057 point 3) calls `pull-request`.

3. **GitHub only, through `gh`, and labelled.** The command is written for a repository hosted on GitHub: it uses GitHub's merge queue, GraphQL fields and squash-commit defaults. COR-014 lets content tied to one harness stay in core under a label naming it ("Scoping content that fails the test"). This record applies the same rule to one hosting service, so the command's reference is labelled GitHub-specific. Version 1 of its documents deliberately uses GitHub's vocabulary (`SQUASH`, `PR_TITLE`, the states of a queue entry). On another service `gh` cannot answer, the reading comes back unreadable, and nothing lands. **When to revisit:** when a second hosting service is supported. The command then becomes the contract, with documents in a vocabulary of their own under a new `schema_version`, and `gh` becomes one implementation behind it.

4. **No hosting-service settings in the backbone.** The command runs `gh` from the caller's working directory, whose git remote names the repository, and in the caller's environment, which names the host (`GH_HOST`). The backbone keeps no setting for host, owner or repository. project-management keeps its host in its own configuration and passes it on through the environment ([DEC-023](../../../.pkit/capabilities/project-management/decisions/DEC-023-gh-host-and-owner.md)). If the backbone ever needs a configuration key of its own for this, only a core record can introduce it ([COR-048](../../../.pkit/decisions/core/COR-048-backbone-configuration.md) point 2).

5. **The command makes requests; the caller decides.** The command sends requests and reports what the service answers. Everything else belongs to the caller. That covers when to land: its gates, its refusals, and whether to enqueue again a head the queue dropped (`--force`). It also covers what happens after a merge: moving issues, running hooks, deleting the head branch. Every caller that lands a pull request keeps four obligations. These are the obligations [DEC-026](../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md) ("Merging through a queue") sets for project-management's verbs, here applied to every caller:
   - **Merged means the service says merged.** On a base that requires a queue, a merge request enqueues the PR and still reports success. So after a direct merge the caller reads the PR again, and runs nothing that follows a merge until a reading says merged.
   - **A PR whose head moved is taken out of the queue.** The requests and the wait are pinned to the head the caller's gates checked. If a reading shows another head, the caller takes the PR out of the queue, so commits nobody checked do not merge.
   - **An unconfirmed merge is reported as unconfirmed.** If a request got no answer, or the service cannot be read after a request it may have accepted, the caller reports the PR as neither queued nor merged. It runs nothing that follows a merge, and stops as accepted so that running it again completes the landing.
   - **The head branch is deleted only after the merge.** The caller deletes the head branch only once the service reports the PR merged. Deleting it earlier closes a queued PR.

   The steps that make up a landing (read, refuse, merge or enqueue, wait, take the PR out if its head moved) are written twice today: once in project-management's `land`, once in `pkit release merge`. **When to move them into the command:** when a third caller appears, or when the two copies first disagree ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)).

6. **The command guards the changes it makes.** `merge`, `enqueue` and `dequeue` change the hosting service. Each runs the cross-repository guard before its request, whether it is called as a command or imported. The guard asks at a terminal and refuses when there is none, and a caller can pass a confirmation with each call (COR-039 points 1–2; [ADR-034](ADR-034-foreign-repo-mutation-guard.md) points 1 and 4). A caller whose operator has already confirmed the change passes that confirmation on, so nobody is asked twice. The readings and the wait change nothing, so they run no guard. Each caller still guards the changes it makes itself.

7. **The JSON documents are the contract.** With `--json`, each subcommand writes JSON documents, one per line, each carrying a `schema_version`. A caller decides on the documents' fields and refuses a version it does not know. A reading states its own conclusions (merged, queued, dropped at its current head), so no caller works them out again. A missing document means there was no answer: the request may or may not have been made, so the caller reads the PR before it decides. Exit codes are for a person at a terminal. One code may cover several outcomes, so no caller decides on an exit code. Adding a field keeps the version. Removing or redefining a field raises the version, which makes it a breaking command-line change ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)), and the reading capability's supported backbone range moves with it.

8. **The rule for how a PR lands is set here.** The backbone lands a pull request as one squash commit on its base: its subject is the PR title and its body is the PR body. The command merges only by squash and takes the subject from its caller. A merge queue builds the commit from the repository's squash-commit defaults and ignores what a request passes. So before it enqueues, a caller checks that the queue squashes and that the defaults are `PR_TITLE` and `PR_BODY`, and refuses otherwise. The backbone's code and references cite this record for this rule. DEC-013 keeps the same rule for project-management's verbs and cites this record for the mechanic.

## Rationale

**Why the backbone.** Both callers need the mechanic, and they sit on different layers: one in a capability, one in the backbone. The backbone cannot call a capability, because an adopter may not install it. So the backbone is the only home both can reach. There is one home rather than two because drift here closes PRs (#1200), the reasoning behind one home per computation (ADR-057 point 2). Capability scripts run on their own and do not import the backbone's package. That is why they reach it by command, and why the documents (point 7) must be a stable contract.

**Why GitHub's vocabulary, and no adapter layer.** With only one service, a neutral vocabulary would just be GitHub's renamed. Merge queues, auto-merge and squash-commit defaults are GitHub's concepts. A second service, such as GitLab with its merge trains, would differ in ways one example cannot predict. COR-007 extracts a common form only once a pattern recurs, and point 3 names the recurrence that triggers it.

**Why the environment carries the host.** The capability already keeps its host and passes it on through the environment (DEC-023), and `gh` finds the repository from the git remote. A backbone key would duplicate a capability setting, and would need a core record (COR-048) for a fact the caller already has.

**Why the obligations are stated rather than built in.** Each obligation spans steps that belong to the caller: its gates before the merge and its follow-up after. The two copies also fail differently. One reaches the command as a separate process, where a request can go unanswered; the other imports the module. Moving the shared steps into the command now would build in a shape that a third caller has not yet confirmed. Stating the obligations lets both copies be reviewed against one list until the trigger fires.

**Why the command runs the guard (point 6).** COR-039 puts the check in the program that makes the change. This command now makes the hosting-service change that every landing passes through. The gap COR-039 accepts is a raw tool used around the methodology, not one of the methodology's own commands. An unguarded `pkit pull-request merge` would therefore be a hole in the protection, not one of its stated limits. Placing the check in the command covers every caller, including `pkit release merge`, which runs no guard today.

### Alternatives considered

- **A hosting-service adapter layer now:** a neutral interface with GitHub as one implementation. Rejected: there is only one service, so the interface would be GitHub's shape under new names (point 3; COR-007).
- **Keep the mechanic in the capability and copy it into the release flow.** Rejected: two copies drift, and this drift closed PRs. The backbone also cannot import a capability.
- **Put these acts under `repository`.** Rejected: it would add network acts to the command COR-054 made local and network-free, which commands bound by the query contract rely on (point 2).
- **Treat the command as plumbing and leave the guard to callers.** Rejected: that relies on every caller remembering to guard, and the backbone's own caller does not (point 6).
- **Let callers decide on exit codes.** Rejected: one code cannot say which of several outcomes happened. For example, `wait` exits with 3 both when the PR left the queue and when its head moved.

## Implications

- **Citations, once this record is accepted.** DEC-013's "One merge mechanic" paragraph and its rationale cite this record. So do the module's placement note, the CLI reference's "Pull-request commands" and the release README, which cite it, not DEC-013, for how the backbone lands a PR.
- **Follow-up: the guard (point 6).** No backbone command runs the cross-repository guard today. The guard exists only in project-management's library. The command's mutating subcommands gain it, together with a flag for passing a confirmation with each call, which project-management's verbs pass on once their own guard has passed. The comparison the guard makes then lives in the backbone, and the capability's guard reaches it by command instead of keeping a second copy. Until this lands, the CLI reference states that these subcommands run no guard.
- **Follow-up: moving the landing steps into the command (point 5).** Filed together with its trigger. Until the trigger fires, any change to either copy is reviewed against point 5's obligations. Both copies also delete the head branch after a merge, and that code is kept in step in the same way.
- **Follow-up: check the remote tip before deleting.** Both copies delete the remote head branch after the merge without checking that its tip is the head that merged, so a push made after the merge would be lost. Deletion should require that check, as deleting the local branch already does.
- **Follow-up: the commit body on a direct merge.** A direct merge passes the subject but no body, which leaves the body to the service. To meet point 8, either the command passes the PR body, or callers check the repository defaults on a direct merge as well.
- **Accept this record before the release.** `pkit pull-request` is a public command of the backbone. This record is accepted before the release that ships it.
