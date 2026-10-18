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

**Preconditions:** None.

**Assumptions:**

- A prompt is the harness's own act, and the permission hook sees only that it deferred a call. So what the session logs is a superset of the real prompts (PRJ-006 point 2).

**Trigger:** The operator keeps being asked to confirm commands the agents run.

**Main path:**

1. The operator runs `pkit permissions diagnose on`.
2. The system arms a diagnostic session for a bounded time. It says that the log is local and git-ignored.
3. The agents work as usual. For each call the permission hook defers to the harness, the system appends the call to the log, with its command's tail redacted.
4. The operator runs `pkit permissions diagnose report`.
5. The system groups the logged calls by the shape of their command. It ranks the groups by frequency within four bands: defects, recommendations, judgement calls, and what can only be documented.
6. The system tells the real prompts from the rest:
   - the logged calls the harness's settings allow anyway, which never prompted
   - the real prompts whose every segment is allowed, which only their chaining made prompt
   - the real prompts no allow rule covers
7. For each group, the system names a remediation, such as granting a catalog privilege or narrowing to single commands. It applies none of them.
8. The operator applies the chosen remediations, such as with `pkit permissions grant <subject> <privilege>`.
9. The operator runs `pkit permissions diagnose off`, and the hook stops logging.

**Variants:**

- **1a.** The agent's command was blocked, not prompted. The permission hook's reason reaches the session, such as `deny grant for agent:project-manager on ['issue-tracker-write']`. The operator runs `pkit permissions explain`. Its list of each subject's grants marks each guardrail, and names the capability behind each deny a capability contributed (ADR-016). A guardrail cannot be granted around. The diagnostic session logs no denied call, and the use case ends.
- **1b.** The operator sets the session's length with `--ttl <seconds>`, eight hours by default, or logs whole commands with `--no-redact`. The path goes on at step 2.
- **3a.** The permission hook is not registered, so nothing logs a call. The report finds nothing, and says to arm a session and work. It does not say that the hook is off.
- **3b.** The session's time runs out. The hook stops logging, and `pkit permissions diagnose status` shows `EXPIRED` (PRJ-006 point 5).
- **3c.** The log reaches its cap, 2000 entries by default. The system drops the oldest entries first.
- **3d.** Logging a call fails. The hook's decision stands, and nothing is logged for that call (PRJ-006 point 2).
- **5a.** A file tool was deferred on a target in the agent workspace. The report puts that deferral first, in a `workspace` group in its band of defects. Every agent is granted the agent workspace. So the remediation is to check the active profile and enforcement, or to report a bug (ADR-060 point 7).
- **8a.** A remediation needs a privilege the catalog lacks. Defining a privilege is the operator's own task, which no fix may ever do unattended (PRJ-006 point 4).

**Postconditions:** The operator knows which commands prompted and how often, and which change of the operator's own would stop each group.

**Minimal guarantees:**

- Logging never changes a decision, and a fault in it never blocks a call (PRJ-006 point 2 and `diagnose_capture.py`).
- A diagnostic session ends on its own once its time is up, so it never stays on unnoticed (PRJ-006 point 5).
- The report applies nothing (PRJ-006 point 3 and `permissions.py`).
- The log stays local and git-ignored, and redacts each command's tail unless the operator asks otherwise (PRJ-006 point 5).
