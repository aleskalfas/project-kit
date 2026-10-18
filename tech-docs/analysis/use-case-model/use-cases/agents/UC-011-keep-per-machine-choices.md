---
id: UC-011
title: Keep my per-machine choices out of what the project commits
status: active
actor: ACT-operator
other-actors: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/permissions.py
        - src/project_kit/visibility.py
        - src/project_kit/install.py
      record:
        - ADR-007
        - ADR-008#4
        - ADR-009#7
        - ADR-010#3
        - ADR-010#4
        - ADR-010#7
        - ADR-029#1
        - ADR-029#3
        - ADR-032
        - ADR-046#1
        - PRJ-006#5
      artefact:
        - ACT-operator
---

# UC-011 — Keep my per-machine choices out of what the project commits

**Goal:** Keep my per-machine choices (sandbox allowances, sockets, local settings) out of what the project commits.

**Other actors:** None.

**Preconditions:** None.

**Assumptions:**

- Git ignores `.claude/settings.local.json`, through the project's `.gitignore` or the harness. The backbone never writes the project's `.gitignore`, and `pkit init` only recommends the line (ADR-009 point 7). Where git does not ignore the file, nothing in the system stops it being committed.

**Trigger:** The operator makes a choice that holds on this machine alone, such as letting the sandbox reach the SSH agent's socket.

**Main path:**

1. The operator runs `pkit permissions sandbox accommodate --socket "$SSH_AUTH_SOCK"`.
2. The system writes the socket's allowance to the `sandbox` block of `.claude/settings.local.json`, and says `(narrowing, per-machine, NOT committed)`.
3. The system records in `.pkit/permissions/project/sandbox-provenance.yaml` that pkit wrote the entry. A later run then replaces only that entry (ADR-010 point 4).
4. The operator commits the project's work.
5. Git leaves both files out. The project's `.gitignore` ignores the first, and the `.pkit/.gitignore` that pkit renders ignores the second (ADR-009 point 7).

**Variants:**

- **1a.** The operator excludes a command from the sandbox with `pkit permissions sandbox exclude <command>`. The system writes the exclusion to `.claude/settings.local.json`, never to a committed file (ADR-008 point 4).
- **1b.** The operator turns the sandbox on with `pkit permissions sandbox enable`, or off with `pkit permissions sandbox disable`. The system writes `sandbox.enabled`, and the strict seal where asked, to `.claude/settings.local.json`. What every operator shares goes to the committed `.claude/settings.json`, such as `failIfUnavailable` and the credential `denyRead` floor (ADR-029 point 1 and ADR-032).
- **1c.** The operator activates a profile with `pkit permissions profile activate <name>`. The system writes the profile's name to `.pkit/permissions/project/active-profile.yaml`. It writes the allow rules only that profile justifies to `.claude/settings.local.json` (ADR-046 point 1). The profile's posture counts as shared policy, so it goes to the committed `.pkit/permissions/project/config.yaml` (ADR-032).
- **1d.** The operator arms a diagnostic session with `pkit permissions diagnose on`. Its marker and its log lie under `.pkit/permissions/project/`, where `.pkit/.gitignore` ignores them (PRJ-006 point 5).
- **1e.** The operator runs `pkit permissions setup autonomy`. The system moves each per-machine entry an earlier version left in a committed file to its per-machine home. The system leaves the operator's own entries where they are (ADR-007).
- **2a.** The socket's path lies under the credential floor. The system still writes the allowance, since the operator chose it, and warns that the sandbox may still block it (ADR-010 point 7).

**Postconditions:** Each per-machine choice is in force on this machine, and no commit carries it.

**Minimal guarantees:**

- A widening, such as a command excluded from the sandbox, is never written to a committed file (ADR-008 point 4 and ADR-029 point 3).
- A value read from this machine, such as a socket's path, is never written to a committed file (ADR-010 point 3).
- A move of a per-machine entry writes the per-machine file before it strips the committed one, so no entry is lost between the two (`permissions.py`).
