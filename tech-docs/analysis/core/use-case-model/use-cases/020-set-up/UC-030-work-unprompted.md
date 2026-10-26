---
id: UC-030
title: Let agents work on their own without a stream of confirmations
status: active
actor: ACT-operator
other-actors:
  - ACT-ai-agent
after:
  - [UC-014, UC-049]
  - [UC-014, UC-019, UC-049]
requirements:
  - REQ-002
  - REQ-005
  - REQ-009
  - REQ-012
  - REQ-013
  - REQ-016
shortfalls:
  - at: 2
    issue: "#1765"
    record: ADR-034#1
  - at: "1b"
    issue: "#1884"
    record: COR-004
  - at: "4a"
    issue: "#1909"
    record: COR-028#2
  - at: "4c"
    issue: "#1764"
    record: ADR-002#4
  - at: "5a"
    issue: "#1765"
    record: ADR-014#3
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/permissions.py
        - .pkit/permissions/decide.py
        - .pkit/permissions/profiles/autonomous.yaml
        - .pkit/adapters/README.md
      record:
        - COR-028#1
        - COR-028#2
        - COR-028#3
        - ADR-002#4
        - ADR-004#2
        - ADR-004#4
        - ADR-005#2
        - ADR-007
        - ADR-010#5
        - ADR-010#7
        - ADR-014#2
        - ADR-014#3
        - ADR-014#4
        - ADR-027
        - ADR-030
        - ADR-025#1
        - ADR-025#2
        - ADR-028
        - ADR-029#2
        - COR-004
        - ADR-034#1
      artefact:
        - ACT-operator
        - ACT-ai-agent
        - REQ-002
        - REQ-005
        - REQ-009
        - REQ-012
        - REQ-013
        - REQ-016
---

# UC-030 — Let agents work on their own without a stream of confirmations

**Goal:** Let agents work on their own without a stream of confirmations, and know where their confinement does not hold.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): each agent that works under the permission model. A [grant](../../../glossary.md#term-grant--grant) lets the agent's commands run with nobody asked. The permission code denies the agent each [guardrail](../../../glossary.md#term-guardrail--guardrail), and the [harness](../../../glossary.md#term-harness--harness)'s settings deny the guardrails' common forms too, such as `git push --force` ([COR-028 point 2](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md#2-the-adapter-realizes-the-model)).

**Preconditions:**

- **From UC-014 or UC-049:** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.
- **From UC-014, UC-019 or UC-049:** An [adapter](../../../glossary.md#term-adapter--adapter) for the project's [harness](../../../glossary.md#term-harness--harness) declares where that harness enforces each dimension of the permission model ([COR-028 point 3](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md#3-unenforceable-intent-is-reported-not-dropped)).

**Assumptions:**

- The [harness](../../../glossary.md#term-harness--harness) enforces what its settings declare: the native allows and denies, the registered [permission hook](../../../glossary.md#term-permission-hook--permission-hook) and the [sandbox](../../../glossary.md#term-sandbox--sandbox). The [adapter](../../../glossary.md#term-adapter--adapter)'s enforcement declaration says which layer carries each dimension of the permission model ([COR-028 point 3](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md#3-unenforceable-intent-is-reported-not-dropped)).
- The harness reads the sandbox's settings only when a session starts, so the sandbox takes effect with the next session ([ADR-007 point 4](../../../../../architecture/decisions/ADR-007-setup-command-class.md#4-honest-boundaries)).

**Trigger:** The operator wants the agents to work without asking for a confirmation of each command.

**Main path:**

1. The operator runs `pkit permissions setup autonomy`.
2. At its entry, before it reads anything, the command checks that the repository it would write in is the session's own. Where it is another, the [system](../../../glossary.md#term-system--system) asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit permissions setup autonomy` runs no such check, and writes in whatever repository holds its working directory. [ADR-034 point 1](../../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system activates the `autonomous` [profile](../../../glossary.md#term-profile--profile), whose grants it layers beneath the [project](../../../glossary.md#term-project--project)'s own grants. It then realises the permission model in the [harness](../../../glossary.md#term-harness--harness)'s settings ([ADR-005 point 2](../../../../../architecture/decisions/ADR-005-permission-profile-surface.md#2-contents--posture-plus-a-layered-grant-source-confinement-and-native-allow-referenced-not-owned) and [COR-028 point 2](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md#2-the-adapter-realizes-the-model)).
4. The system registers the [adapter](../../../glossary.md#term-adapter--adapter)'s [permission hook](../../../glossary.md#term-permission-hook--permission-hook) with the harness. It makes sure the harness's settings hold the native denies of the [guardrails](../../../glossary.md#term-guardrail--guardrail) (COR-028 point 2).
5. The system turns the [sandbox](../../../glossary.md#term-sandbox--sandbox) on, fail-closed and sealed ([ADR-004 point 4](../../../../../architecture/decisions/ADR-004-autonomy-intent-confinement.md#4-fail-closed-invariant-on-confinement-conditioned-prompt-suppression) and [ADR-028](../../../../../architecture/decisions/ADR-028-seal-unsandboxed-escape-under-autonomy-posture.md)). In Claude Code's settings, for one, these are:
   - `sandbox.failIfUnavailable: true`, so a session refuses to start without the sandbox
   - `sandbox.autoAllowBashIfSandboxed: true`, so a single command inside the sandbox runs with nobody asked, which ADR-004 point 4 allows only beside the line above
   - `sandbox.allowUnsandboxedCommands: false`, the seal, so no agent can take one command out of the sandbox
   - the credential floor, four credential paths such as `~/.ssh` that no command in the sandbox may read
6. The system adds the narrowing allowances the project's tools need, such as a package cache. It also allows the socket that `$SSH_AUTH_SOCK` names, in the per-machine settings ([ADR-010 point 5](../../../../../architecture/decisions/ADR-010-host-environment-detection.md#5-liveness-honest)).
7. The system stops before it verifies the setup, since the sandbox starts only with a new session. It ends `Result: configured. Restart the session and re-run to enable the box and prove the goal.` ([ADR-007](../../../../../architecture/decisions/ADR-007-setup-command-class.md)).
8. The operator restarts the session, and runs `pkit permissions setup autonomy` again from inside it. The system skips each step already done.
9. The system verifies the setup. Its probes find that the permission code's verdicts match the model, and that the operating system refuses each read of the credential floor. It ends `Result: goal reached — autonomous agents: configured, confined, and proven.`
10. The agents work. The adapter's permission hook runs the [backbone](../../../glossary.md#term-backbone--backbone)'s permission code under the system `python3`, and the code needs nothing outside that interpreter's standard library (REQ-016). A command a [grant](../../../glossary.md#term-grant--grant) allows runs with nobody asked, and so does a single command inside the sandbox. A deny wins over an allow (REQ-013).
11. The operator learns where the confinement does not hold, from commands that write nothing (REQ-005):
    - `pkit permissions sandbox` says whether the sandbox really confines, and names each command that runs outside it
    - `pkit permissions diff` counts the grants that only the permission hook enforces, and those that no native layer expresses
    - `pkit permissions diff` also names each dimension that the adapter's enforcement declaration says no layer enforces, such as `network-egress` ([COR-028 point 3](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md#3-unenforceable-intent-is-reported-not-dropped))

**Variants:**

- **1a.** The operator names another [profile](../../../glossary.md#term-profile--profile) with `--profile <name>`, such as `non-destructive`. The path goes on at step 2 with that profile.
- **1b.** The operator passes `--dry-run`, as to each command whose edit reaches past what the person named. The [system](../../../glossary.md#term-system--system) names each edit it would make, and writes nothing (REQ-009).

> [!WARNING]
> **Not built yet:** `pkit permissions setup autonomy` takes no `--dry-run`, and writes as it goes. [COR-004](../../../../../../.pkit/decisions/core/COR-004-cli-surface.md) decides that each such command offers the flag, and #1884 tracks it.

- **4a.** The installed [adapter](../../../glossary.md#term-adapter--adapter) is another [harness](../../../glossary.md#term-harness--harness)'s than Claude Code's. The system realises the permission model through that adapter, as it does through Claude Code's ([COR-028 point 2](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md#2-the-adapter-realizes-the-model)). The path goes on at step 5.

> [!WARNING]
> **Not built yet:** the system realises the model for Claude Code's adapter alone, and reads only its enforcement declaration. Without that adapter, it writes the profile's activation, then refuses with `the claude-code adapter is not installed in this project; live enforcement is harness-specific, so there is nothing to enable.`. COR-028 point 2 decides that each adapter realises the model, and #1909 tracks it.

- **4b.** The [permission hook](../../../glossary.md#term-permission-hook--permission-hook) is registered already, and the profile is active. The system skips steps 3 and 4, so it restores no native deny missing from the harness's settings. The probes then find the missing deny, and the path goes on at 9a.
- **4c.** The permission hook cannot start, such as where its script is missing. The system reports that enforcement is not running, and never ends `goal reached` while the fault stands ([ADR-002 point 4](../../../../../architecture/decisions/ADR-002-permission-realizer-ownership.md#4-two-fault-classes-a-decision-fault-fails-open-an-enforcement-runtime-fault-fails-loud)).

> [!WARNING]
> **Not built yet:** `setup autonomy` does not name the fault. Its probes call the permission code directly, so it can end `goal reached` with a hook that cannot start. `pkit permissions overview` reports some of the fault's causes. ADR-002 point 4 decides that this fault fails loud, and #1764 tracks it.

- **5a.** The host runs macOS. The system turns the [sandbox](../../../glossary.md#term-sandbox--sandbox) on, and excludes from it each command the platform requires outside it ([ADR-014 point 2](../../../../../architecture/decisions/ADR-014-macos-sandbox-platform-stance.md#2-the-pkit--uv-cli-is-excluded-from-the-os-box)). Those are `uv` until a fixed `uv` is installed, and `gh` where the [project](../../../glossary.md#term-project--project) holds `.github/` ([ADR-014 point 4](../../../../../architecture/decisions/ADR-014-macos-sandbox-platform-stance.md#4-a-version-floor-is-preferred-over-the-exclusion-once-a-fixed-uv-ships), [ADR-027](../../../../../architecture/decisions/ADR-027-required-sandbox-exclusion-auto-apply.md) and [ADR-030](../../../../../architecture/decisions/ADR-030-gh-exclusion-required-subclass-generalises.md)). Every other shell command stays confined, and the system reports the commands that run outside the sandbox ([ADR-014 point 3](../../../../../architecture/decisions/ADR-014-macos-sandbox-platform-stance.md#3-the-trade-off-is-stated-honestly-not-hidden)).

> [!WARNING]
> **Not built yet:** on macOS the system leaves the sandbox off, and says `OS sandbox NOT enabled — unsupported on macOS (Seatbelt)`. So no command is confined there. The run ends `Result: intent + enforcement armed and proven. OS confinement is skipped on macOS (see above).` ADR-014 point 3 decides that every other shell command stays confined, and #1765 tracks it.

- **5b.** An attribute of the per-machine settings fights what step 5 sets, such as `sandbox.allowUnsandboxedCommands: true`. The system warns, naming each such attribute, and step 5 turns the sandbox on and seals it all the same. The system never removes such an attribute without a yes at a terminal, or `--remove-overrides`.
- **6a.** `$SSH_AUTH_SOCK` names a socket under the credential floor, or one that does not respond. The system allows nothing for it, and names the command that allows it: `pkit permissions sandbox accommodate --socket "$SSH_AUTH_SOCK" --name ssh-agent` (ADR-010 points [5](../../../../../architecture/decisions/ADR-010-host-environment-detection.md#5-liveness-honest) and [7](../../../../../architecture/decisions/ADR-010-host-environment-detection.md#7-credential-floor-collision--never-silently-auto-apply)).
- **9a.** A probe finds a verdict that differs from what the model declares. Or it finds a [guardrail](../../../glossary.md#term-guardrail--guardrail)'s native deny missing while the permission hook is registered. The system ends `Result: BROKEN — fix the decision layer before relying on autonomy.`, and exits non-zero.
- **9b.** The run is outside the sandbox, such as from a terminal of its own, or in a session that started before the sandbox was on. The system verifies the permission code's verdicts, and says the credential floor cannot be proven from there. It asks for a restart, and the path rejoins at step 8.
- **9c.** None of the four paths of the credential floor exists on the machine. The system cannot prove the floor, even inside the sandbox. It ends `Result: configured and decision-proven. One step left: restart the session, then re-run to prove the OS confinement floor.`
- **10a.** A command chains segments, which the permission code splits at `&&`, `||`, `|`, `;`, a background `&` and a newline. The code strips a bare leading `cd <path>`, and decides the rest in the same working directory ([ADR-025 point 1](../../../../../architecture/decisions/ADR-025-segment-conservative-bash-allow.md#1-phase-1--strip-a-leading-cd-decide-on-the-remainder)). A `$`, backtick, redirection outside 10d, `(` or `PATH` assignment makes the code defer the call, as does a word the shell reads otherwise ([ADR-025 point 2](../../../../../architecture/decisions/ADR-025-segment-conservative-bash-allow.md#2-inherited-fail-closed-on-uncertainty-adr-004-decision-point-4-non-negotiable)). So does a segment in which it recognises no [privilege](../../../glossary.md#term-privilege--privilege), and otherwise it allows the chain only where grants allow each segment and deny none.
- **10b.** The permission hook meets a fault in a call, such as a payload it cannot read. It defers the call to the harness. The harness's settings still deny the guardrails' common forms ([COR-028 point 2](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md#2-the-adapter-realizes-the-model)).
- **10c.** A glob, or an assignment such as `HOME=…` that changes the program's configuration, may hide a form of a command a deny names. So the code defers `git push origin --forc[e]` whatever the grants allow ([ADR-025 point 2](../../../../../architecture/decisions/ADR-025-segment-conservative-bash-allow.md#2-inherited-fail-closed-on-uncertainty-adr-004-decision-point-4-non-negotiable)). Where the deny is a guardrail, Claude Code's permission hook asks the operator rather than defers, outside auto and bypass mode (`permission-hook.py`). The code denies the forms [ADR-025 point 5](../../../../../architecture/decisions/ADR-025-segment-conservative-bash-allow.md#5-the-deny-side-remains-porous) lists, such as `git push -uf`.
- **10d.** The command holds a redirection that duplicates or closes a file descriptor, such as `2>&1`, or discards output to `/dev/null`, such as `>/dev/null`. The code removes such a redirection first, and decides what is left as it would decide that command typed alone ([ADR-025 point 2](../../../../../architecture/decisions/ADR-025-segment-conservative-bash-allow.md#2-inherited-fail-closed-on-uncertainty-adr-004-decision-point-4-non-negotiable)). A deny binds on a program behind the redirection too. A lookalike such as `2>&1t`, which zsh reads as a write to a file, makes the code defer the call.

**Postconditions:** The agents run each granted command, and each single command inside the [sandbox](../../../glossary.md#term-sandbox--sandbox), with nobody asked. The [system](../../../glossary.md#term-system--system) has verified the permission code's verdicts and the credential floor. The operator knows where the confinement does not hold.

**Minimal guarantees:**

- The [harness](../../../glossary.md#term-harness--harness)'s settings deny the [guardrails](../../../glossary.md#term-guardrail--guardrail)' common forms, such as `sudo`, even where the [permission hook](../../../glossary.md#term-permission-hook--permission-hook) fails or is not registered ([COR-028 point 2](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md#2-the-adapter-realizes-the-model)).
- `setup autonomy` lets commands in the [sandbox](../../../glossary.md#term-sandbox--sandbox) run unasked only together with the setting that stops a session without the sandbox. So a missing sandbox stops the session, rather than letting commands run unconfined and unasked ([ADR-004 point 4](../../../../../architecture/decisions/ADR-004-autonomy-intent-confinement.md#4-fail-closed-invariant-on-confinement-conditioned-prompt-suppression)).
- `setup autonomy` declares the goal reached only once its probes pass ([ADR-007](../../../../../architecture/decisions/ADR-007-setup-command-class.md)).
- The [system](../../../glossary.md#term-system--system) writes the harness's settings only through the permission model's one writer, which routes each entry to its file (REQ-002 and [ADR-029 point 2](../../../../../architecture/decisions/ADR-029-move-mutable-sandbox-state-out-of-tracked-settings.md#2-one-writer-with-routing--not-two-writers)).
- A dimension that the [adapter](../../../glossary.md#term-adapter--adapter)'s enforcement declaration says no layer enforces is reported, never dropped ([COR-028 point 3](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md#3-unenforceable-intent-is-reported-not-dropped) and `permissions.py`).
