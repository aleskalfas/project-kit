---
id: REQ-003
title: No secret goes on a command line
status: active
statement: The system never puts a secret, such as a token or a password, on the command line of a program it starts.
measure: No argument of a process the system starts, and no command line the system gives a person to type, holds a secret.
applies-to: Every command and script that the backbone and the components ship.
actors: []
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-engineering/agents/security-reviewer.md
      record:
        - software-engineering:DEC-002#1
        - PRJ-009
---

# REQ-003 · Quality · No secret goes on a command line

**Verified by:** The security reviewer of software-engineering's review panel withholds its approval from a change of project-kit's code that passes a secret on a command line (PRJ-009). No test checks it.

**Rationale:** Anyone on the machine can read a process's arguments, and logs and shell history keep them, as the security reviewer's agent definition says. software-engineering DEC-002 set up the review panel after report #715 found an authentication token passed so.
