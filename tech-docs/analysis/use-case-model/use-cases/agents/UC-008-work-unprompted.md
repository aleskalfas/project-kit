---
id: UC-008
title: Let agents work on their own without a stream of confirmations
status: active
actor: ACT-operator
other-actors:
  - ACT-ai-agent
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/permissions.py
        - .pkit/permissions/decide.py
        - .pkit/adapters/claude-code/permission-hook.py
        - .pkit/adapters/claude-code/permission-enforcement.yaml
        - .pkit/permissions/profiles/autonomous.yaml
        - .pkit/adapters/claude-code/settings/core/settings.json
      record:
        - COR-028#1
        - COR-028#2
        - COR-028#3
        - ADR-002#3
        - ADR-002#4
        - ADR-004#2
        - ADR-004#3
        - ADR-004#4
        - ADR-005#2
        - ADR-005#6
        - ADR-007
        - ADR-010#5
        - ADR-010#7
        - ADR-014
        - ADR-025
        - ADR-028
      artefact:
        - ACT-operator
        - ACT-ai-agent
---

# UC-008 — Let agents work on their own without a stream of confirmations

**Goal:** Let agents work on their own without a stream of confirmations, and know where their confinement does not hold.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): each agent that works under the permission model. A grant lets the agent's commands run with no prompt. The permission hook denies the agent each guardrail, and the native settings deny the guardrails' common forms too, such as `git push --force` (ADR-002 point 3).

**Preconditions:** The claude-code adapter is installed in the project.

**Assumptions:**

- The harness enforces what the project's settings declare: the native allows and denies, the registered permission hook and the sandbox. The adapter's enforcement declaration says which layer carries each part of the permission model (ADR-004 point 3).
- The harness does not reload `sandbox.enabled` while a session runs, so the sandbox starts with the next session (ADR-007 point 4).

**Trigger:** The operator wants the agents to work without asking for a confirmation of each command.

**Main path:**

1. The operator runs `pkit permissions setup autonomy`.
2. The system activates the `autonomous` profile, whose grants it layers under the project's own grants. It then applies the permission model to the harness's settings (ADR-005 point 2).
3. The system registers the permission hook in `.claude/settings.json`, and makes sure the native guardrail denies are there.
4. The system turns the sandbox on, fail-closed and sealed (ADR-005 point 6 and ADR-028):
   - `sandbox.failIfUnavailable: true`, so a session refuses to start without the sandbox
   - `sandbox.allowUnsandboxedCommands: false`, the seal, so no agent can take one command out of the sandbox
   - the credential floor: four credential paths, such as `~/.ssh`, added to `sandbox.filesystem.denyRead`
5. The system adds the narrowing allowances the project's tools need, such as a package cache. It also allows the socket that `$SSH_AUTH_SOCK` names.
6. The system stops before it verifies the setup, since the sandbox starts only with a new session. It says `Restart the session and re-run to enable the box and prove the goal.`
7. The operator restarts the session, and runs `pkit permissions setup autonomy` again from inside it. The system skips each step already done.
8. The system verifies the setup. Its probes find that the decision core's verdicts match the model, and the operating system refuses access to the credential floor. It ends `Result: goal reached — autonomous agents: configured, confined, and proven.`
9. The agents work. A command a grant allows runs with no prompt, and a single command inside the sandbox runs with no prompt too.
10. The operator learns where the confinement does not hold:
    - `pkit permissions sandbox` says whether the sandbox really confines, and names each command that runs outside it
    - `pkit permissions diff` names the grants only the permission hook enforces, and the grants no native layer expresses
    - `pkit permissions diff` also names each dimension no layer of the harness enforces, such as `network-egress`

**Variants:**

- **1a.** The operator names another profile with `--profile <name>`, such as `non-destructive`. The path goes on at step 2 with that profile.
- **3a.** The permission hook is registered already. The system skips step 3, so it restores no native guardrail deny missing from the settings. The probes then find the missing deny, and the path goes on at 8a.
- **3b.** The permission hook cannot start, such as where `python3` is missing. `setup autonomy` does not report it. Its probes call the decision core directly, so the command can still end `goal reached`. `pkit permissions overview` reports `ENFORCEMENT-RUNTIME FAULT — hook CANNOT START`.
- **4a.** The host runs macOS. The system leaves the sandbox off, and writes `sandbox.enabled: false` to `.claude/settings.local.json` where the sandbox was on. It says why: the sandbox breaks `gh`, `pkit` and `git push` there, so no command is confined on that host. Its probes verify the decision core alone, and it ends `Result: intent + enforcement armed and proven. OS confinement is skipped on macOS (see above).`
- **4b.** An attribute in `.claude/settings.local.json` fights what step 4 sets, such as `sandbox.allowUnsandboxedCommands: true`. The system warns, naming each attribute, and step 4 sets `sandbox.enabled` and the seal all the same. It removes any other such attribute, such as a leftover `sandbox.excludedCommands`, only once the operator confirms at a terminal or passes `--remove-overrides`. The path goes on at step 5.
- **5a.** `$SSH_AUTH_SOCK` names a socket under the credential floor, or one that does not answer. The system allows nothing for it. It names the command that allows it: `pkit permissions sandbox accommodate --socket <path>` (ADR-010 points 5 and 7).
- **8a.** A probe finds a verdict that differs from what the model declares, or a native guardrail deny missing while the permission hook is registered. The system ends `Result: BROKEN — fix the decision layer before relying on autonomy.`, and exits non-zero.
- **8b.** The run is outside the sandbox, such as from a terminal of its own, or in a session that started before the sandbox was on. The system verifies the decision core's verdicts, and says the credential floor is not provable from here. It asks for a restart, and the path rejoins at step 7.
- **9a.** A command chains segments, such as with `;`, `&&` or `|`. The permission hook allows the whole chain where each privilege it recognises in any segment is granted, even `gh pr list | sh` (`decide.py`). Otherwise the hook defers to the harness's own flow, which may ask the operator to confirm the chain. The hook strips a bare leading `cd <path> &&` first (ADR-025).
- **9b.** The permission hook meets a fault in a call, such as a payload it cannot read. It defers to the harness's own flow. The native settings still deny the guardrails' common forms (ADR-002 point 3).

**Postconditions:** The agents run each granted command, and each single command inside the sandbox, with no prompt. The system has verified the decision core's verdicts and the credential floor. The operator knows where the confinement does not hold.

**Minimal guarantees:**

- The native settings deny the guardrails' common forms, such as `sudo`, even where the permission hook fails or is not registered (ADR-002 point 3).
- `setup autonomy` lets commands in the sandbox run with no prompt only together with `sandbox.failIfUnavailable: true` in `.claude/settings.json`. So a missing sandbox stops the session, rather than letting commands run unconfined and unprompted (ADR-004 point 4).
- `setup autonomy` declares the goal reached only once its probes pass (ADR-007 point 5).
- A dimension the adapter declares no layer enforces is reported, never dropped (COR-028 point 3 and `permissions.py`).
