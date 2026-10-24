---
id: REQ-060
title: A secret never goes on a command line
status: active
statement: Code never passes a secret, such as a token, a password or an API key, to another process on its command line.
measure: "No change the `security-reviewer` approved passes a secret to a process as an argument: in an argument list, in a shell command's string, or as a flag's value. Each secret reaches the process through its environment, a file with restricted permissions, or its standard input."
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

**Rationale:** A process's arguments can be read by every user of the machine, such as through `ps`, and are logged and kept in shell history, as the `security-reviewer` says. A pull request once passed the merge gate approved with a token passed to a subprocess as an argument, since nothing reviewed its code (software-engineering DEC-002). So the reviewer treats such a secret as an objective defect, never a judgement call.
