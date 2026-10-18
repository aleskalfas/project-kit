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

- **AI agent** (`ACT-ai-agent`): each agent that works under the permission model. A grant lets the agent's commands run with no prompt. A guardrail denies the agent the catastrophic commands, such as `git push --force`, on two layers (ADR-002 point 3).

**Preconditions:** None.

**Assumptions:**

- The harness enforces what the project's settings declare: the native allows and denies, the registered permission hook and the sandbox. The adapter's enforcement declaration says which layer carries each part of the permission model (ADR-004 point 3).
- The harness does not reload `sandbox.enabled` while a session runs, so the sandbox starts with the next session (ADR-007 point 4).
- A grant spares a prompt, and confines nothing. A shell command reaches past any check of its working directory, so only the sandbox confines it (ADR-004 point 2).

**Trigger:** The operator wants the agents to work without asking for a confirmation of each command.

**Main path:**

1. The operator runs `pkit permissions setup autonomy`.
2. The system activates the `autonomous` profile, whose grants it layers under the project's own grants. It then applies the permission model to the harness's settings (ADR-005 point 2).
3. The system registers the permission hook in `.claude/settings.json`, and makes sure the native guardrail denies are there.
4. The system turns the sandbox on, fail-closed and strict, with the credential `denyRead` floor. A session then refuses to start without the sandbox, and no agent can turn the sandbox off for one command (ADR-028).
5. The system adds the narrowing allowances the project's tools need, such as a package cache, and the socket that `$SSH_AUTH_SOCK` names.
6. The system stops at the session restart, and says `Restart the session and re-run to enable the box and prove the goal.`
7. The operator restarts the session and runs `pkit permissions setup autonomy` again. The system skips each step already done.
8. The system proves the goal. Its probes find that the hook's decisions match the model, and the operating system refuses access to the credential floor. It ends `Result: goal reached — autonomous agents: configured, confined, and proven.`
9. The agents work. A command a grant allows runs with no prompt, and so does a single command inside the sandbox. The hook and the native settings deny each guardrail.
10. The operator runs `pkit permissions diff` to learn where the confinement does not hold. The command names three kinds of gap:
    - the grants only the hook enforces
    - the grants no native layer expresses
    - the dimensions no layer of the harness enforces, such as `network-egress`

**Variants:**

- **1a.** The operator names another profile with `--profile <name>`, such as `non-destructive`. The path goes on at step 2 with that profile.
- **3a.** The hook cannot start, such as where `python3` is missing. `setup autonomy` does not report it. Its probes call the decision core directly, so the command can still end `goal reached`. `pkit permissions overview` reports `ENFORCEMENT-RUNTIME FAULT — hook CANNOT START`.
- **4a.** The host runs macOS. The system leaves the sandbox off, and writes `enabled: false` to `.claude/settings.local.json`. It says why: the sandbox breaks `gh`, `pkit` and `git push` there. Its probes prove the hook's decisions alone, and it ends `Result: intent + enforcement armed and proven. OS confinement is skipped on macOS (see above).` No command is confined on that host.
- **4b.** An attribute in `.claude/settings.local.json` overrides the intended posture, such as `allowUnsandboxedCommands: true`. The system warns, naming each attribute. It removes them only once the operator confirms at a terminal, or passes `--remove-overrides`. The path goes on at step 5.
- **5a.** `$SSH_AUTH_SOCK` names a socket under the credential floor, or one that does not answer. The system allows nothing for it, and names the command that would: `pkit permissions sandbox accommodate --socket <path>` (ADR-010 points 5 and 7).
- **8a.** A probe finds a decision that differs from what the model declares. The system ends `Result: BROKEN — fix the decision layer before relying on autonomy.`, and exits non-zero.
- **8b.** The settings turn the sandbox on, and this session started before they did. The system proves the hook's decisions, says the floor is not provable from here, and asks for a restart. The path rejoins at step 7.
- **9a.** A command chains statements, such as with `;` or `|`, or substitutes one with `$(…)`. The harness asks the operator to confirm it, even inside the sandbox. A bare leading `cd <path> &&` is the one prefix the hook strips (ADR-025).
- **9b.** The hook meets a fault in a call, such as a payload it cannot read. It defers to the harness's own flow, and the native denies still hold each guardrail (ADR-002 point 3).

**Postconditions:** The agents run each granted command, and each single command inside the sandbox, with no prompt. The system has proven the hook's decisions and the credential floor, and has named each gap in the confinement.

**Minimal guarantees:**

- The native settings deny each guardrail, even where the hook fails or is not registered (ADR-002 point 3).
- The system turns on commands that run in the sandbox with no prompt only with `failIfUnavailable: true`. So a missing sandbox stops the session, rather than letting commands run unconfined and unprompted (ADR-004 point 4).
- `setup autonomy` declares the goal reached only once its probes pass (ADR-007 point 5).
- An intent the harness cannot enforce is reported, never dropped (COR-028 point 3 and `permissions.py`).
