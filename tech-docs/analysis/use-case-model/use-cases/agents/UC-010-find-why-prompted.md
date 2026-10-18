---
id: UC-010
title: Find out why a command prompted me or was blocked
status: active
actor: ACT-operator
other-actors:
  - ACT-ai-agent
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/permissions.py
        - .pkit/permissions/diagnose_capture.py
        - .pkit/permissions/decide.py
        - .pkit/adapters/claude-code/permission-hook.py
        - .pkit/adapters/claude-code/settings/core/settings.json
      record:
        - PRJ-006#1
        - PRJ-006#2
        - PRJ-006#3
        - PRJ-006#4
        - PRJ-006#5
        - COR-028#1
        - ADR-016
        - ADR-060#7
      artefact:
        - ACT-operator
        - ACT-ai-agent
---

# UC-010 — Find out why a command prompted me or was blocked

**Goal:** Find out why a command prompted me or was blocked, and what would stop it happening again.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): each agent whose commands the operator was asked to confirm. The diagnostic session logs the agent's deferred calls, and changes no decision on them (PRJ-006 point 2).

**Preconditions:** The claude-code adapter is installed in the project.

**Assumptions:**

- The harness asks for a confirmation only on a call the permission hook deferred, or on one the hook asked about itself. The hook cannot see whether the harness asked, so what the diagnostic session logs is a superset of the real prompts (PRJ-006 point 2).

**Trigger:** The operator keeps being asked to confirm commands the agents run.

**Main path:**

1. The operator runs `pkit permissions diagnose on`.
2. The system arms a diagnostic session for a bounded time. It says that the log is local and git-ignored.
3. The agents work as usual. For each call the permission hook defers to the harness, the system appends the call to the log, with its command's tail redacted.
4. The operator runs `pkit permissions diagnose report`.
5. The system groups the logged calls by the shape of their command. It ranks the groups by frequency within three bands, in this order: defects, recommendations and judgement calls.
6. The system flat-matches each logged call against the allow rules of the harness's settings files, and splits the calls three ways:
   - the calls an allow rule matches, which the report counts as never prompted
   - the other calls whose every segment an allow rule matches, which only their chaining made prompt
   - the rest, which no allow rule covers
7. For each group, the system names a remediation, such as granting a catalog privilege or narrowing to single commands. It applies none of them.
8. The operator applies the chosen remediations, such as with `pkit permissions grant <subject> <privilege>`.
9. The operator runs `pkit permissions diagnose off`, and the hook stops logging.

**Variants:**

- **1a.** The permission hook denied the agent's command, so the diagnostic session logs nothing of it. The hook's reason reaches the agent's session, such as `deny grant for agent:project-manager on ['issue-tracker-write']`. The operator runs `pkit permissions explain`, whose list of each subject's grants marks each guardrail and names each deny a capability contributed (ADR-016). The use case ends.
- **1b.** The `strict` posture denied the command, since no grant allows it. The hook's reason is `strict posture: nothing grants this request`. A grant of the privilege, or a profile with the `lenient` posture, would let the command run. The use case ends.
- **1c.** The permission hook is not registered, and a native deny of the settings blocks the command, such as `Bash(sudo:*)`. The harness gives its own message, and nothing is logged. The use case ends.
- **1d.** The sandbox stopped the command from reaching a file or a host. The command fails with the operating system's error, the hook gives no reason, and nothing is logged. The use case ends.
- **1e.** The operator sets the diagnostic session's length with `--ttl <seconds>`, eight hours by default, or logs whole commands with `--no-redact`. The path goes on at step 2.
- **3a.** The permission hook is not registered, so nothing logs a call. The report finds nothing, and says to arm a diagnostic session and work. The report does not say that the hook is off.
- **3b.** The diagnostic session's time runs out. The hook stops logging, and `pkit permissions diagnose status` shows `EXPIRED` (PRJ-006 point 5).
- **3c.** The log reaches its cap, 2000 entries by default. The system drops the oldest entries first.
- **3d.** Logging a call fails. The hook's decision stands, and nothing is logged for that call (PRJ-006 point 2).
- **3e.** The permission hook asks the operator about an `Edit` or a `Write` outside the session anchor (UC-009). The system logs that call as a deferral. The settings allow both tools, so the report counts the call as never prompted.
- **5a.** A file tool was deferred on a target in the agent workspace. The report puts that deferral first, in a `workspace` group in the band of defects. Every agent is granted the `workspace` privilege. So the remediation is to check the active profile and enforcement, or to report a bug (ADR-060 point 7).
- **8a.** A remediation needs a privilege the catalog lacks. Defining a privilege is the operator's own task, which no fix may ever do unattended (PRJ-006 point 4).

**Postconditions:** The operator knows which calls the permission hook deferred and how often, and which change of the operator's own would stop each group of prompts.

**Minimal guarantees:**

- Logging never changes a decision, and a fault in it never blocks a call (PRJ-006 point 2 and `diagnose_capture.py`).
- A diagnostic session ends on its own once its time is up, so it never stays on unnoticed (PRJ-006 point 5).
- The report applies nothing (PRJ-006 point 3 and `permissions.py`).
- The log stays local and git-ignored, and redacts each command's tail unless the operator asks otherwise (PRJ-006 point 5).
