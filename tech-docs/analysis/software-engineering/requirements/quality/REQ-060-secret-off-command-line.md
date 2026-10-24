---
id: REQ-060
title: A secret never goes on a command line
status: active
statement: No change the `security-reviewer` approves puts a secret, such as a token, a password or an API key, on another process's command line.
measure: "Each change the `security-reviewer` approved passes no secret to a process as an argument. That holds for an argument list, a shell command's string and a flag's value."
applies-to: "Every change whose code starts another process, in a project that runs the `security-reviewer` of the code-review panel."
actors: []
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-engineering/agents/security-reviewer.md
        - .pkit/capabilities/software-engineering/review-contributions.yaml
      record:
        - software-engineering:DEC-002#1
        - software-engineering:DEC-002#3
        - project-management:DEC-032#D1
---

# REQ-060 · Quality · A secret never goes on a command line

**Verified by:** The `security-reviewer` judges each pull request whose diff touches code. It blocks one that owns such a secret: one the change introduces, exposes, moves, copies or widens, or claims to remove (software-engineering DEC-002 point 3). No test or check finds such a secret, and no test pins the reviewer's instruction to block on one.

**Rationale:** Every user of the machine can read a process's arguments, such as through `ps`, and logs often keep them. So a secret there leaks to whoever can read the machine, as the `security-reviewer` says. The reviewer treats such a secret as an objective defect, never a judgement call. A pull request once passed the merge gate with a token passed to a subprocess as an argument, since nothing reviewed its code (software-engineering DEC-002).
