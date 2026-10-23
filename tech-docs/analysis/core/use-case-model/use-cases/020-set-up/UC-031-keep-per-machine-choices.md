---
id: UC-031
title: Keep my per-machine choices out of what the project commits
status: active
actor: ACT-operator
other-actors: []
after:
  - [UC-014]
  - [UC-014, UC-019]
requirements:
  - REQ-002
  - REQ-009
  - REQ-012
shortfalls:
  - at: 2
    issue: "#1765"
    record: ADR-034#1
  - at: "1g"
    issue: "#1884"
    record: COR-004
  - at: "3a"
    issue: "#1909"
    record: COR-028#2
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/permissions.py
        - src/project_kit/visibility.py
        - src/project_kit/install.py
      record:
        - ADR-005#6
        - ADR-007
        - ADR-008#4
        - ADR-009
        - ADR-010#3
        - ADR-010#4
        - ADR-010#7
        - ADR-029#1
        - ADR-029#2
        - ADR-029#3
        - ADR-032
        - ADR-046#1
        - PRJ-006#5
        - COR-004
        - ADR-034#1
        - COR-028#2
      artefact:
        - ACT-operator
        - REQ-002
        - REQ-009
        - REQ-012
---

# UC-031 — Keep my per-machine choices out of what the project commits

**Goal:** Keep my per-machine choices (sandbox allowances, sockets, local settings) out of what the project commits.

**Other actors:** None.

**Preconditions:**

- **From UC-014:** The project runs the system: it is the methodology's source repository, or the system is installed in it.
- **From UC-014 or UC-019:** An adapter for the project's harness declares where that harness enforces each dimension of the permission model (COR-028 point 3).

**Assumptions:**

- The harness reads a per-machine settings file beside its committed one, and the per-machine file's values win over the committed one's. Claude Code's `.claude/settings.local.json` is such a file (ADR-029 point 1).
- Git ignores that per-machine file, through the project's `.gitignore`. The backbone never writes the project's `.gitignore`, and `pkit init` only recommends the line (ADR-009). Where git does not ignore the file, nothing in the system stops a commit carrying it.

**Trigger:** The operator makes a choice that holds on this machine alone, such as letting the sandbox reach the SSH agent's socket.

**Main path:**

1. The operator runs `pkit permissions sandbox accommodate --socket "$SSH_AUTH_SOCK"`.
2. At its entry, before it reads anything, each writing command of this use case checks that the repository it would change is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** no `pkit permissions` command runs such a check, and each writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system writes the socket's allowance to the sandbox's settings in the per-machine file, never in a committed one (ADR-010 point 3). It says `socket accommodated (manual): allow-unix-socket <path> (narrowing, per-machine, NOT committed).`
4. The system records in `.pkit/permissions/project/sandbox-provenance.yaml` that the entry is its own. A later run then replaces only that entry (ADR-010 point 4).
5. The operator commits the project's work.
6. Git leaves both files out. The project's `.gitignore` ignores the per-machine settings file. The `.pkit/.gitignore` that the system renders ignores the provenance file (ADR-009 point 7).

**Variants:**

- **1a.** The operator excludes a command from the sandbox with `pkit permissions sandbox exclude <command>`. The system writes the exclusion to the per-machine settings, never to a committed file (ADR-008 point 4).
- **1b.** The operator turns the sandbox on with `pkit permissions sandbox enable`, or off with `pkit permissions sandbox disable`. The system writes `sandbox.enabled`, and the seal where `--strict` asks for it, to the per-machine settings (ADR-029 point 1 and ADR-032). What every operator shares goes to the committed settings, such as the credential paths that no command in the sandbox may read.
- **1c.** The operator turns the sandbox on with `--dangerously-allow-unconfined`. The system writes `sandbox.failIfUnavailable: false` to the per-machine settings alone, and the committed settings keep `true` (ADR-005 point 6). It warns where git does not ignore the per-machine file.
- **1d.** The operator activates a profile with `pkit permissions profile activate <name>`. The system writes the profile's name to `.pkit/permissions/project/active-profile.yaml`, which `.pkit/.gitignore` ignores (ADR-032). It writes the allows only that profile justifies to the per-machine settings (ADR-046 point 1). ADR-032 calls the posture shared policy, so the system writes it to the committed `.pkit/permissions/project/config.yaml`, though ADR-032's Rule A reads it as per-machine (#1765).
- **1e.** The operator arms a diagnostic session with `pkit permissions diagnose on`. Its marker and its log lie under `.pkit/permissions/project/`, where `.pkit/.gitignore` ignores them (PRJ-006 point 5).
- **1f.** The operator runs `pkit permissions setup autonomy` (UC-030). The system writes the per-machine parts of the setup to the per-machine settings, and the shared parts to the committed ones. It moves each entry an earlier version left in a committed file to that entry's per-machine home (ADR-007). It leaves the operator's own entries in place.
- **1g.** The operator passes `--dry-run` to a command of this use case whose edit reaches past what the person named, such as `sandbox enable`. The system names each edit it would make, and writes nothing (REQ-009).

> [!WARNING]
> **Not built yet:** `sandbox accommodate`, `sandbox enable`, `profile activate` and `setup autonomy` take no `--dry-run`. COR-004 decides that each such command offers the flag, and #1884 tracks it.

- **3a.** The installed adapter is another harness's than Claude Code's. The system writes the allowance through that adapter, to its harness's per-machine settings (COR-028 point 2). The path goes on at step 4.

> [!WARNING]
> **Not built yet:** the system realises the model for Claude Code's adapter alone. Without that adapter, it refuses with `the claude-code adapter is not installed; the sandbox is harness-specific.`, and writes nothing. COR-028 point 2 decides that each adapter realises the model, and #1909 tracks it.

- **3b.** The socket's path lies under a credential path that no command in the sandbox may read, such as `~/.ssh`. The system still writes the allowance, since the operator chose it, and warns that the sandbox may still block it (ADR-010 point 7).

**Postconditions:** Each per-machine choice is in force on this machine, in a file no commit carries. What the system counts as shared policy, such as a profile's posture, goes to a committed file.

**Minimal guarantees:**

- An exclusion from the sandbox is never written to a committed file (ADR-008 point 4 and ADR-029 point 3).
- A value read from this machine, such as a socket's path, is never written to a committed file (ADR-010 point 3).
- The fail-open that `--dangerously-allow-unconfined` asks for is never written to a committed file (ADR-005 point 6).
- The system writes the harness's settings only through the permission model's one writer, which routes each entry to its file (REQ-002 and ADR-029 point 2).
- A move of a per-machine entry writes the per-machine file first, then strips the committed one. So no entry is lost between the two (`permissions.py`).
