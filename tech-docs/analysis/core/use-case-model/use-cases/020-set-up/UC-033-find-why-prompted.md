---
id: UC-033
title: Find out why a command prompted me or was blocked
status: active
actor: ACT-operator
other-actors:
  - ACT-ai-agent
after:
  - [UC-014]
  - [UC-014, UC-019]
requirements:
  - REQ-005
  - REQ-012
  - REQ-016
shortfalls:
  - at: 2
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/permissions.py
        - src/project_kit/visibility.py
        - .pkit/permissions/diagnose_capture.py
        - .pkit/permissions/decide.py
      record:
        - PRJ-006#1
        - PRJ-006#2
        - PRJ-006#3
        - PRJ-006#4
        - PRJ-006#5
        - COR-028#1
        - ADR-016
        - ADR-060#7
        - ADR-034#1
      artefact:
        - ACT-operator
        - ACT-ai-agent
        - REQ-005
        - REQ-012
        - REQ-016
---

# UC-033 — Find out why a command prompted me or was blocked

**Goal:** Find out why a command prompted me or was blocked, and what would stop it happening again.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): each agent whose commands the operator was asked to confirm. The diagnostic session logs the agent's deferred calls, and changes no decision on them (PRJ-006 point 2).

**Preconditions:**

- **From UC-014:** The project runs the system: it is the methodology's source repository, or the system is installed in it.
- **From UC-014 or UC-019:** An adapter for the project's harness declares where that harness enforces each dimension of the permission model (COR-028 point 3).

**Assumptions:**

- The harness asks for a confirmation only on a call the permission hook deferred, or on one the hook asked about itself. The hook cannot see whether the harness asked, so the log holds more calls than the real prompts (PRJ-006 point 2).

**Trigger:** The operator keeps being asked to confirm commands the agents run.

**Main path:**

1. The operator runs `pkit permissions diagnose on`.
2. At its entry, before it reads anything, each writing command of this use case checks that the repository it would change is the session's own. Those are `diagnose on`, `diagnose off` and `pkit permissions grant`. Where the repository is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** none of those three commands runs such a check, and each writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system arms a diagnostic session for a bounded time, eight hours by default (PRJ-006 points 1 and 5, and `permissions.py`). It says that the log is local and ignored by git.
4. The agents work as usual. The permission hook defers some calls to the harness. For each, it has the backbone's capture code append the call to the log, its command's tail redacted (PRJ-006 point 2). That code needs only the system `python3` (REQ-016).
5. The operator runs `pkit permissions diagnose report`, which writes nothing (REQ-005).
6. The system matches each logged call against the allow rules of the harness's settings files, and splits the calls three ways:
   - the calls an allow rule matches whole, which the report counts as never prompted
   - the chained shell commands whose every segment an allow rule matches, which only their chaining made prompt
   - the rest, which no allow rule covers
7. The system groups the logged calls, and ranks the groups by frequency within bands, in this order: defects, recommendations and judgement calls.
8. For each group, the system names a remediation, such as granting a privilege of the catalog, or narrowing a chain to single commands. It applies none of them (PRJ-006 point 3).
9. The operator applies the chosen remediations, such as with `pkit permissions grant <subject> <privilege>` (UC-022).
10. The operator runs `pkit permissions diagnose off`, and the hook stops logging. The log stays.

**Variants:**

- **1a.** The permission hook denied the agent's command, so the diagnostic session logs nothing of it. The hook's reason reaches the agent's session, such as `deny grant for agent:<name> on ['issue-tracker-write']`. The operator runs `pkit permissions explain`, which writes nothing and lists each subject's grants, marking guardrails and grants from capabilities (REQ-005, ADR-016). The use case ends.
- **1b.** The `strict` posture denied the command, since no grant allows it. The hook's reason is `strict posture: nothing grants this request`. A grant of the privilege would let the command run, and a `lenient` posture would have the hook defer it to the harness instead. The use case ends.
- **1c.** A native deny of the harness's settings blocks the command, such as `Bash(sudo:*)` in Claude Code's. The harness gives its own message, and nothing is logged. The use case ends.
- **1d.** The sandbox stopped the command from reaching a file or a host. The command fails with the operating system's error, the hook gives no reason, and nothing is logged. The use case ends.
- **1e.** The operator sets the diagnostic session's length with `--ttl <seconds>`, or logs whole commands with `--no-redact`. The path goes on at step 2.
- **4a.** The permission hook is not registered, so nothing logs a call. The report finds nothing, and says to arm a diagnostic session and work. It does not say that the hook is off.
- **4b.** The diagnostic session's time runs out. The hook stops logging, and `pkit permissions diagnose status` shows `EXPIRED` (PRJ-006 point 5).
- **4c.** The log reaches its cap, 2000 entries. The system drops the oldest entries first (PRJ-006 point 5 and `diagnose_capture.py`).
- **4d.** Logging a call fails. The hook's decision stands, and nothing is logged for that call (PRJ-006 point 2).
- **4e.** The hook asks the operator about a file write outside the session anchor, as Claude Code's does (UC-032). The log holds that call as a deferral. The harness's settings allow the file tools, so the report counts the call as never prompted (#1764).
- **7a.** A file tool was deferred on a target in the agent workspace. The report puts that deferral first, in its `workspace` group in the band of defects (ADR-060 point 7). Every agent is granted the `workspace` privilege, so the remediation is to check the active profile and enforcement, or to report a bug.
- **9a.** A remediation needs a privilege the catalog lacks. Defining a privilege is the operator's own task, which no fix may ever do unattended (PRJ-006 point 4).

**Postconditions:** The operator knows which calls the permission hook deferred and how often, and which change of the operator's own would stop each group of prompts.

**Minimal guarantees:**

- Logging never changes a decision, and a fault in it never blocks a call (PRJ-006 point 2 and `diagnose_capture.py`).
- A diagnostic session ends on its own once its time is up, so it never stays on unnoticed (PRJ-006 point 5).
- The report applies nothing (PRJ-006 point 3 and REQ-005).
- The log stays local and ignored by git, and redacts each command's tail unless the operator asks otherwise (PRJ-006 point 5).
