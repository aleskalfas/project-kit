---
id: ADR-060
title: "Path-scoped allows: the agent workspace as a privilege recognised from the target path"
status: accepted
date: 2026-09-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

Agents need one place for their intermediate files where writing never makes the operator confirm anything, so the permission catalog gains a new kind of privilege — a *path-scoped allow*, recognised only when a file tool's target lies inside a named folder — and every shipped profile grants the agent workspace, `.agent-workspace/` at each checkout's root, to every agent. It reduces prompts on the allow side and confines nothing. A shell command writing into the folder is judged exactly as any other shell write; for the file tools, which the OS sandbox does not wrap, this allow *is* the gate inside the folder — so the folder counts only as the checkout itself holds it: never through a symlink, never from an absolute or climbing catalog entry, never in another repository or in one nested inside it. This is a refinement child of [ADR-004](ADR-004-autonomy-intent-confinement.md) and refines [ADR-005](ADR-005-permission-profile-surface.md)'s shipped-profile table; [ADR-025](ADR-025-segment-conservative-bash-allow.md) stands unchanged.

## Context

Issue #1043 recorded the cost: an agent keeps intermediate files somewhere — pull-request and issue bodies, scripts, captured output — and every write outside the working directory asks the operator, one file at a time, for the whole session, until the operator approves harmless confirmations without reading them. That is the confirmation fatigue the permission model exists to prevent ([COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md)). The harness's own per-session scratch directory did not help: it lies outside a subagent's working directory, and absolute allow rules written for it did not stop the prompts. The answer the issue settled on is one git-excluded folder per checkout that the permission model grants to every agent; the backbone declares and creates it (a rule in `rules/core.md`, `pkit init` / `sync` / `status`), the permission capability grants it, and each adapter translates the grant.

Granting it needed something the catalog did not have. Privileges were recognised by the tool named (`recognize.tool`) or by the command's leading words (`recognize.bash`), and a grant's `directory` scope matches the request's *cwd* — and a scoped allow **denies** the privilege outside its scope. A `Write` / `Edit` grant scoped to the folder would therefore have denied every write elsewhere. The workspace needs the opposite: a privilege that exists only inside the folder and has no opinion outside it.

The first implementation also recognised shell writes into the folder — an `echo` / `printf` / `cat` redirected into it, a literal here-document, `rm` of files in it — and let such a write through [ADR-025](ADR-025-segment-conservative-bash-allow.md)'s leading-`cd` strip. Review proved that unsound (see Rationale), and the file tools already do the job with the target in plain sight. This record fixes the shape that remains.

As project-kit's own architecture record, harness specifics are in scope. It was accepted, as a child of foundational ADR-004, before the change it records merged, after the architect's review.

## Decision

**The catalog gains a path-scoped allow: a privilege recognised only for a listed file tool whose resolved target lies inside one of its folders at a checkout root. The agent workspace is its shipped instance, granted to every agent by every shipped profile, realised by the hook and never as a settings rule. Shell commands are out of it entirely: ADR-025 stands unchanged.**

1. **Recognition from the target path, for the file tools only.** A privilege may carry `recognize.path: {folders, tools}`. It is recognised for a request only when the request's tool is one of `tools` and the path the tool names — resolved against the request's working directory, symlinks resolved — lies strictly inside one of `folders`. It is never recognised for the tool alone, and never for a shell command. Outside its folders it has no opinion: a request there is decided exactly as without it. An existing file with more than one link is not recognised: a hard link planted in the folder would carry a write to its other name. The workspace lists `Read`, `Write`, `Edit`, `MultiEdit` and `NotebookEdit`.

2. **The folder is the checkout's own.** A folder is named relative to a checkout root, never absolute, never starting with `~`, never climbing out with `..`; the recogniser ignores any other entry, so a capability's catalog fragment ([ADR-021](ADR-021-capability-contributed-privilege-definitions.md)) cannot declare `/` or the directory above the project. The folder counts only when it is reached through no symlink — resolving `<resolved checkout>/<folder>` must change nothing — so a symlinked `.agent-workspace` is never the workspace. The shipped folder is a direct child of the checkout root.

3. **Which checkouts count.** The project root, and another working tree of the same repository: the main one, whose `.git` is the common git directory, or a linked worktree that git registered there — its `.git` pointer names `<common>/worktrees/<id>` and that entry points back at it. A planted `.git` pointer does not make a worktree, and another repository's workspace never counts (the cross-repository rule, `rules/core.md` rule 19). Nor does a repository or worktree nested inside the folder: when any directory from the folder down to the target holds a `.git` entry, the target is not in the workspace.

4. **No Bash exception.** ADR-025 stands unchanged. A shell write into the workspace fails closed like any other: after a stripped leading `cd`, a redirect or a quote in the remainder abstains; without a `cd`, the command is decided on its own grants, and nothing about the folder grants it.

5. **Granted to `all` by every shipped profile**, `read-only` included — the folder is excluded from version control and holds nothing a commit can carry. ADR-005's shipped-profile table lists it (its point 5).

6. **Realised by the hook, never as a settings rule.** The projection reports a path-scoped grant as `runtime`: a session-wide `Write` or `Edit` rule would reach far beyond the folder. The Claude Code adapter emits no rule, because inside its working directory the harness already approves reads, accepted edits and sandboxed commands; an adapter whose harness does not would emit the narrowest path-scoped rule its harness offers. The adapter's enforcement declaration names the dimension `path-scoped-allow` (hook, runtime) — explicitly **not** a confinement boundary: it only removes prompts. Shell reach is `filesystem-confinement`, the sandbox's ([ADR-004](ADR-004-autonomy-intent-confinement.md)); the file tools run outside the sandbox, so inside the folder the recogniser's precision (points 1–3) is what separates an allow from the rest of the disk.

7. **A prompt there is a defect.** Every agent is granted the workspace, so the diagnostic loop tags a deferred file-tool request whose target the recogniser places in the folder and reports it in its own DEFECTS band, ahead of every recommendation — never as an allowlist gap to tune around.

8. **Code home, and one reading of `.git`.** The recogniser lives in the shared decision core, `.pkit/permissions/decide.py` ([ADR-003](ADR-003-permission-core-code-home.md)'s same-code invariant). It enters through the tool branches only — `recognized_privileges` adds the path-scoped hits to a tool request's, and `hook_decide` passes the file tool's target and the project root; `decide()` itself is unchanged. The hook runs in-box without git ([ADR-014](ADR-014-macos-sandbox-platform-stance.md)), so it reads `.git` by hand; the backbone's answer from git itself is held to that reading by a conformance test.

9. **Excluded per clone; the committed ignore line is recommended, never written.** `pkit init` and `pkit sync` exclude the folder in the common git directory's `info/exclude` — one entry for every worktree of the clone — and refuse a symlink in the folder's place. The project's committed `.gitignore` is the adopter's file, which the backbone never writes ([ADR-009](ADR-009-git-footprint-visibility.md)), so `init` recommends the line that covers every clone. Until a clone runs `init` or `sync`, or the project commits that line, the committed hook already grants a folder git does not yet ignore — the `git add -A` exposure ADR-009 closed for `.pkit/`; `pkit status` reports it. This is the fresh decision ADR-009's rule 7 requires for a runtime-local artifact outside `.pkit/`.

## Rationale

**Why a recogniser, not a grant scope.** A scope narrows where a privilege is *allowed* and denies it elsewhere — right for `docker` limited to a directory, wrong for a folder that should add an allow without taking any away. Putting the folder into recognition makes the privilege simply absent outside it, so a grant can neither reach nor deny a file elsewhere, and every other reader of the catalog (the settings projection, rule attribution) — which reads only `tool` and `bash` — cannot mistake it for a session-wide tool allow.

**Why the target path, not the working directory.** The working directory says nothing about where a file tool writes; an absolute `file_path` lands wherever it names. The file tools carry their target in plain sight, which is what makes them honestly inspectable ([ADR-034](ADR-034-foreign-repo-mutation-guard.md) relies on the same property for its cross-repository check).

**Why no shell recogniser.** A shell expands a command's words before it runs them, and the decision core's dumb splitter cannot see what they expand to — by design, since hosting a shell parser in the hook was rejected on altitude grounds (ADR-025 point 3). Review proved each attempt to read a shell write as "only a file in the folder" wrong:

- zsh process substitution, `echo =(touch PWNED) > .agent-workspace/x`, runs a command inside an emitter's argument with no `$(` on the line;
- zsh's `(e)` parameter flag and bash 5's `${…@P}` prompt expansion evaluate an escaped substitution at expansion time, again with no literal `$(`;
- `cd .agent-workspace/nope; rm -f *` read `*` relative to the `cd` directory, but when the `cd` fails, `;` runs `rm` in the original directory and empties the project root;
- and the architect's review found four more holes in the here-document reading.

Each is the composition problem ADR-025 names when it rejects the all-segments-safe widening as unsound; a blocklist, then an allowlist, of shell syntax only moves the boundary. The file tools do the same work with nothing to expand, and `rules/core.md` rule 15 already prefers the harness's dedicated tools over ad-hoc shell.

**Why "the checkout's own" folder.** A hostile repository can commit `.agent-workspace` as a symlink to the home directory; if the grant followed it, every agent could write anywhere under it. A capability fragment declaring `/` or `..` would do the same from the catalog side. Refusing any folder not literally inside the resolved checkout closes both, and the registered-worktree check keeps a planted `.git` pointer from extending the grant to a directory git never made a worktree.

**Why every shipped profile, `read-only` included.** The workspace grant carries no repository change: the folder is excluded from version control, and the read-only tier's intent — nothing an agent does reaches the repository — is unchanged by it. Leaving it out would bring back, under the strictest profile, exactly the prompts #1043 removes.

**Why `path-scoped-allow`, not `path-confinement`.** ADR-004 and [ADR-019](ADR-019-enforcement-gate-mechanism-vs-boundary.md) insist a mechanism is declared for what it is. The hook keyed on a path reduces prompts; it bounds nothing an agent can reach — a shell command still writes wherever the sandbox lets it. Naming the dimension after confinement would invite exactly the misreading of a tighter allow path as a boundary that ADR-025 warns against.

### Alternatives considered

- **A `directory`-scoped `Write` / `Edit` grant.** Rejected — a scoped allow denies outside its scope, so it would deny every write elsewhere.
- **Recognising shell writes into the folder** (an emitter or `rm` whose every target lies inside, a literal here-document, and a leading-`cd` exception for them). Rejected — the proofs of concept above: arbitrary execution through an emitter's expanded arguments, and a deletion outside the folder when a `cd` fails. The first implementation of #1043 took this path; it is reverted, and ADR-025 needs no amendment.
- **A session-wide settings rule for the folder** (a `Write` / `Edit` allow on its path). Rejected for Claude Code — inside the working directory the harness already approves the folder, and a rule keyed on one checkout's absolute path neither covers worktrees nor stays inside the folder once written session-wide. The projection keeps the seam for a harness that needs one.
- **The harness's own per-session scratch directory.** Rejected — it lies outside a subagent's working directory, and allow rules written for it did not stop the prompts (#1043's field note).
- **Appending the ignore line to the adopter's `.gitignore`**, with a marker comment. Rejected — ADR-009 settled that no `.gitignore` the adopter owns is ever written, and [COR-002](../../../.pkit/decisions/core/COR-002-merge-delivery.md) rejected in-file markers; `init` prints the recommendation instead, pkit's standing "print, don't mutate" disposition toward adopter git state.

## Implications

- **A new catalog shape.** `recognize.path` joins `tool` and `bash` in the privilege-catalog schema, with `folders` and `tools` both required. It is a pure addition — no `schema_version` bump, no migration — and a surface change: the backbone's changeset declares the new privilege and the workspace, the claude-code adapter's the new enforcement dimension.
- **The verdict path moves only on the tool side.** `decide()` stays byte-identical to its prior form; `recognized_privileges` and `hook_decide` change in their tool branches only, and a test pins the shell verdicts to the previous decision core's. `pkit permissions probe` passes the project root as the live hook does, naming the subject it probes, so it demonstrates the workspace verdict.
- **#1043's third criterion is met for the file tools only.** Its "create, read, edit and delete including shell redirects into it" is deliberately not met for deletion and shell redirects, for the reasons above; agents write the workspace with the file tools, and the rule and every agent body say so.
- **ADR-005 is refined in place,** not superseded: its point 5 has every shipped profile grant `workspace` to `all`. ADR-025 is unchanged.
- **Child of ADR-004; supersedes nothing.** The intent / confinement split, the fail-open hook with its fail-closed native denies, and the speed-bump-not-boundary posture are unchanged; this refines how the intent axis recognises one kind of request.
